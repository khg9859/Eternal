# -*- coding: utf-8 -*-
"""
Hybrid RAG (SQL + pgvector) — Schema-specific single file

Tables
- metadata(metadata_id PK, mb_sn, mobile_carrier, gender, birth_year, age, region)
- codebooks(codebook_id PK, codebook_data JSON/JSONB, q_vector VECTOR)
- answers(answer_id PK, mb_sn, question_id, answer_value, a_vector VECTOR)

Flow
1) gpt-4o-mini로 사용자 문장을 filters(JSON) + semantic_query로 분리
2) filters로 metadata WHERE 만들어 mb_sn 화이트리스트 취득
3) semantic_query 임베딩 → codebooks.q_vector와 유사도 검색해 question_id 상위 k 선택
4) answers에서 (question_id ∈ 선택집합) AND (mb_sn ∈ 화이트리스트) 교차 필터
   + a_vector와 semantic_query 임베딩 유사도로 정렬
5) (선택) gpt-4o-mini로 재랭킹 후, filters/semantic_query/샘플10개를 종합해 서술형 요약 생성
"""

import os, json, re
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

import psycopg2
from psycopg2.extras import RealDictCursor

from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np

import sys

# search 모듈 경로 추가 (parsing.py, makeSQL.py 재사용)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_DIR = os.path.join(BASE_DIR, "search")
if SEARCH_DIR not in sys.path:
    sys.path.append(SEARCH_DIR)

from parsing import parse_query_with_gpt
from makeSQL import build_metadata_where_clause

# -----------------------
# ENV
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing")
oai = OpenAI(api_key=OPENAI_API_KEY)

DB = dict(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

# 임베딩 모델 (KURE)
EMB_MODEL_NAME = os.getenv("EMB_MODEL_NAME", "nlpai-lab/KURE-v1")
_device = "cuda" if os.getenv("USE_CUDA", "0") == "1" else "cpu"
_embedder = SentenceTransformer(EMB_MODEL_NAME, device=_device)

# pgvector: cosine 연산자 사용시 '<=>'
PGVECTOR_OP = "<=>"   # L2면 '<->' 로 교체

# -----------------------
# 1) 자연어 → (filters, semantic_query)
# -----------------------
# ⚠️ 기존 버전에서는 이 파일 내부에 SYSTEM_PROMPT / SCHEMA / parse_query / build_where
#     함수를 모두 정의해서 사용했지만,
#     지금은 `search/parsing.py`, `search/makeSQL.py`에 있는 공용 유틸을 재사용합니다.
#
# - `parse_query_with_gpt(user_query: str)`:
#      OpenAI gpt-4o-mini를 사용해서
#      {"filters": [...], "semantic_query": "..."} 형태의 JSON 딕셔너리를 반환합니다.
#
# - `build_metadata_where_clause(filters, table_name="metadata")`:
#      filters 리스트를 받아서
#      ("WHERE ...", [params...]) 형태의 튜플을 반환합니다.
#
# 이 아래부터는 DB / 임베딩 / 메인 파이프라인 로직만 유지합니다.

# -----------------------
# 3) DB util
# -----------------------
def db_conn():
    return psycopg2.connect(**DB, cursor_factory=RealDictCursor)

# -----------------------
# 4) 벡터 유틸
# -----------------------
def embed(text: str) -> np.ndarray:
    if not text:
        text = "general preference"
    v = _embedder.encode([text], normalize_embeddings=True)[0]  # cosine용 정규화
    return v.astype(np.float32)

# -----------------------
# 5) 객관식 번호 → 라벨(보기 텍스트) 변환 유틸
# -----------------------
_MULTI_SEP = re.compile(r"[,\s]+")

def _build_choice_map(codebook_data: dict) -> dict:
    """
    codebooks.codebook_data['answers']의 보기표를 {코드(str): 라벨(str)}로 변환
    값키: qi_val / q_val / value
    라벨키: qi_title / label / text / name
    """
    m = {}
    if not codebook_data:
        return m
    items = codebook_data.get("answers") or []
    for it in items:
        if not isinstance(it, dict):
            continue
        key = str(it.get("qi_val") or it.get("q_val") or it.get("value") or "").strip()
        val = (it.get("qi_title") or it.get("label") or it.get("text") or it.get("name") or "").strip()
        if key and val:
            m[key] = val
    return m

def _translate_answer_value(raw_value: str, choice_map: dict) -> str:
    """
    "1,2,5" -> "경영/인사/총무/사무, 재무/회계/경리, ..."
    중복 제거 + 순서 보존
    """
    if raw_value is None:
        return ""
    parts = [p for p in _MULTI_SEP.split(str(raw_value).strip()) if p]
    labels = [choice_map.get(p, p) for p in parts]
    seen, out = set(), []
    for x in labels:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return ", ".join(out)

def _attach_human_readable_labels(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        cmap = _build_choice_map(r.get("codebook_data"))
        r["answer_value_text"] = _translate_answer_value(
            r.get("answer_value"), cmap
        ) if cmap else r.get("answer_value")
        out.append(r)
    return out

# -----------------------
# 6) 파이프라인
# -----------------------
def hybrid_answer(
    user_query: str,
    k_questions: int = 5,
    k_answers: int = 500,
    topn_return: int = 1,
) -> Dict[str, Any]:
    print(f"\n{'=' * 25}\n[ RAG 파이프라인 시작 ]\n- 사용자 질문: \"{user_query}\"\n{'=' * 25}")

    # 0단계: 입력 검증 - 인사말이나 의미 없는 입력 필터링
    print("\n[ 0단계: 입력 검증 ]")

    # 간단한 인사말/잡담 패턴
    casual_patterns = [
        "안녕",
        "하이",
        "헬로",
        "hi",
        "hello",
        "ㅎㅇ",
        "ㅎㅎ",
        "뭐해",
        "심심",
        "놀아줘",
        "재밌",
        "ㅋㅋ",
        "ㄷㄷ",
        "에이",
        "아",
        "어",
        "음",
        "으",
        "ㅇㅇ",
    ]

    query_lower = user_query.lower().strip()

    # 너무 짧거나 의미 없는 입력
    if len(query_lower) < 3:
        return {
            "answer": "질문이 너무 짧습니다. 데이터 분석과 관련된 구체적인 질문을 해주세요. 예: '30대 남성의 직업 분포는?'",
            "filters": [],
            "semantic_query": "",
            "question_ids": [],
            "samples": [],
        }

    # 인사말이나 잡담 감지
    if any(pattern in query_lower for pattern in casual_patterns):
        return {
            "answer": "안녕하세요! 저는 패널 데이터 분석 AI입니다. 데이터와 관련된 질문을 해주세요.\n\n예시:\n- '30대 남성의 직업 분포는?'\n- '서울에 사는 사람들의 소비 패턴은?'\n- 'SKT 사용자들의 만족도는?'",
            "filters": [],
            "semantic_query": "",
            "question_ids": [],
            "samples": [],
        }

    print(f"  - 입력 검증 통과: 데이터 분석 질문으로 판단")

    # 1단계: 자연어 질의 분석 (LLM 호출) — 외부 모듈 사용
    print("\n[ 1단계: 자연어 질의 분석 ]")
    parsed = parse_query_with_gpt(user_query)
    filters = parsed.get("filters", [])
    semantic_query = parsed.get("semantic_query", "").strip()
    print(f"  - 분석 결과 (Filters): {json.dumps(filters, ensure_ascii=False)}")
    print(f'  - 분석 결과 (Semantic Query): "{semantic_query}"')

    # 2단계: 메타데이터 필터 → mb_sn 화이트리스트
    print("\n[ 2단계: 메타데이터 필터링 ]")
    where_sql, params = build_metadata_where_clause(filters, table_name="metadata")
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT mb_sn FROM metadata {where_sql};", params)
        mb_list = [r["mb_sn"] for r in cur.fetchall()]
    mb_set = set(mb_list)
    print(f"  - 실행된 SQL: SELECT mb_sn FROM metadata {where_sql};")
    print(f"  - SQL 파라미터: {params}")
    print(f"  - 찾은 응답자 수: {len(mb_set)}명")
    if len(mb_set) > 0:
        print(f"  - 찾은 응답자 샘플: {list(mb_set)[:5]}...")

    # 3단계: 관련 질문 검색 (codebooks.q_vector 상위 k)
    print("\n[ 3단계: 관련 질문 검색 ]")
    q_vec = embed(semantic_query)
    print(f"  - Semantic Query를 벡터로 변환 완료 (차원: {len(q_vec)})")
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT codebook_id
            FROM codebooks
            ORDER BY q_vector {PGVECTOR_OP} %s::vector
            LIMIT %s;
            """,
            (q_vec.tolist(), k_questions),
        )
        qids = [r["codebook_id"] for r in cur.fetchall()]
    print(f"  - 가장 관련성 높은 질문 ID {len(qids)}개 찾음: {qids}")

    if not qids:
        return {
            "answer": "관련 질문을 찾지 못했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": [],
            "sources": [],
        }

    # 4단계: answers 교차 필터 + a_vector 유사도 정렬 (+ codebooks 조인)
    print("\n[ 4단계: 하이브리드 답변 검색 ]")
    print(f"  - 검색 조건: 응답자 {len(mb_set)}명, 질문 ID {qids}")

    # 쿼리 문을 미리 정의 (유지보수 용이)
    sql_select_base = f"""
        SELECT a.answer_id, a.mb_sn, a.question_id, a.answer_value,
               a.a_vector {PGVECTOR_OP} %s::vector AS distance,
               c.codebook_data
        FROM answers a
        LEFT JOIN codebooks c ON a.question_id = c.codebook_id
    """
    sql_order_limit = f"""
        ORDER BY a.a_vector {PGVECTOR_OP} %s::vector
        LIMIT %s
    """

    with db_conn() as conn, conn.cursor() as cur:
        rows = []

        # [시도 1] 필터(mb_sn)와 시맨틱(qids) 교집합 검색
        if mb_set:
            print("  - [시도 1] 필터(mb_sn) + 시맨틱(qids) 교집합 검색 시도...")
            sql_strict = f"""
                {sql_select_base}
                WHERE a.question_id = ANY(%s) AND a.mb_sn = ANY(%s)
                {sql_order_limit};
            """
            params_strict = (
                q_vec.tolist(),
                qids,
                list(mb_set),
                q_vec.tolist(),
                k_answers,
            )
            cur.execute(sql_strict, params_strict)
            rows = cur.fetchall()
            print(f"    -> {len(rows)}건 찾음")

        # [시도 2] 교집합 결과가 0건이면, 시맨틱(qids)만으로 재검색
        # (mb_set이 처음부터 없었거나, 시도 1의 결과가 0건일 때 실행)
        if not rows:
            if mb_set:  # 시도 1이 실패했을 때만 이 로그를 찍음
                print(
                    "  - [시도 2] 교집합 결과 0건. 시맨틱(qids)만으로 재검색합니다."
                )
            else:
                print("  - [시도 1] 필터(mb_sn) 없음. 시맨틱(qids)만으로 검색합니다.")

            sql_loose = f"""
                {sql_select_base}
                WHERE a.question_id = ANY(%s)
                {sql_order_limit};
            """
            params_loose = (q_vec.tolist(), qids, q_vec.tolist(), k_answers)
            cur.execute(sql_loose, params_loose)
            rows = cur.fetchall()
            print(f"    -> {len(rows)}건 찾음")

    print(f"  - 최종 검색된 답변 후보 수: {len(rows)}개")

    if not rows:
        return {
            "answer": "조건에 맞는 응답을 찾지 못했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": qids,
            "sources": [],
        }

    # 응답자 수 통계 계산
    unique_respondents = set(r["mb_sn"] for r in rows)
    print(f"  - 총 {len(unique_respondents)}명의 응답자가 답변함")

    # 객관식 번호 → 라벨 텍스트 부착
    rows = _attach_human_readable_labels(rows)

    # 5단계: LLM 재랭킹 건너뛰기 (모든 데이터 사용)
    print("\n[ 5단계: LLM 재랭킹 건너뛰기 ]")
    print(
        f"  - 벡터 유사도 기반으로 이미 정렬된 {len(rows)}개의 답변을 모두 사용합니다."
    )
    print(
        f"  - LLM 재랭킹을 건너뛰고 전체 데이터를 분석에 활용합니다."
    )

    # 모든 rows를 final로 사용
    final = rows

    # 6단계: 서술형 요약 생성
    print("\n[ 6단계: LLM 요약 생성 ]")
    print(f"  - 최종 {len(final)}개 답변을 기반으로 서술형 요약 생성 요청...")

    # 응답 내용 분석 및 통계 계산
    from collections import Counter

    # 답변 값들을 카운트
    answer_values = [
        r.get("answer_value_text") or r.get("answer_value") or "" for r in final
    ]
    answer_counter = Counter(answer_values)

    # 상위 항목 추출
    top_answers = answer_counter.most_common(10)

    # 응답 내용 텍스트 (번호/ID 제거, 라벨 사용)
    final_text = "\n".join(
        f"- {r.get('answer_value_text') or r.get('answer_value') or ''}"
        for r in final
    )

    # 통계 텍스트 생성
    stats_text = "\n".join(
        [
            f"  • {value}: {count}명 ({count/len(final)*100:.1f}%)"
            for value, count in top_answers
        ]
    )

    # 최종 응답자 수 계산
    final_respondents = set(r["mb_sn"] for r in final)

    summary_prompt = f"""
당신은 데이터 분석가입니다. 아래의 조건과 응답 샘플을 참고해 사용자의 질문에 대해
**구체적인 수치를 포함한 서술형 요약**을 작성하세요.

[통계 정보]
- 총 응답자 수: {len(unique_respondents)}명
- 분석 대상 응답자: {len(final_respondents)}명
- 분석 답변 수: {len(final)}개

[조건]
- filters: {json.dumps(filters, ensure_ascii=False)}
- semantic_query: "{semantic_query}"

[답변 분포 (상위 10개)]
{stats_text}

[지침]
1) **반드시 구체적인 수치와 비율을 포함**하세요. 예: "의사 15명(30%), 간호사 10명(20%)"
2) 가장 많은 답변부터 순서대로 언급하세요.
3) 전체 응답자 수와 비율을 명확히 표시하세요.
4) "다양한 직업군" 같은 애매한 표현 대신 구체적인 수치를 사용하세요.
5) 2-3문단으로 작성하되, 첫 문단에는 주요 통계를, 두 번째 문단에는 세부 내용을 포함하세요.

[질문]
{user_query}

[응답 샘플]
{final_text}

[출력 형식 예시]
"분석 결과, 총 30명의 응답자 중 의사가 15명(50%)으로 가장 많았으며, 간호사 8명(26.7%), 엔지니어 4명(13.3%) 순으로 나타났습니다. 
이 외에도 변호사 2명(6.7%), 회계사 1명(3.3%) 등이 있었습니다."
"""
    try:
        summ = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2,
        )
        answer = summ.choices[0].message.content
        print("  - 서술형 요약 생성 완료.")
    except Exception as e:
        print(f"  - 요약 생성 실패: {e}")
        answer = "요약 생성 중 오류가 발생했지만, 관련 응답 샘플을 반환합니다."

    return {
        "answer": answer,
        "filters": filters,
        "semantic_query": semantic_query,
        "question_ids": qids,
        "samples": final[:topn_return],  # 4단계 결과를 상위 N개 슬라이싱
        "statistics": {
            "total_respondents": len(unique_respondents),
            "analyzed_respondents": len(final_respondents),
            "total_answers": len(rows),
            "analyzed_answers": len(final),
        },
    }

# quick manual test
if __name__ == "__main__":
    q = "서울 사는 30대 남성 중 SKT 사용자들의 경제 만족도와 불만 요인을 요약해줘"
    res = hybrid_answer(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))
