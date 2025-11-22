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
5) GPT로 통계 + 샘플을 자연어로 요약 (대화체, 존댓말)

이 파일은 "엔진 역할" (DB 연결, 벡터 검색, 통계 수집, 요약 생성)에 집중하고,
chat_with_state()가 대화형 챗봇 레이어를 제공한다.
"""

import os
import sys
import re
import json
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

import psycopg2
from psycopg2.extras import RealDictCursor

from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np

# search 모듈 (Eternal_SV/search) 에 있는 공용 유틸 사용
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from search.parsing import parse_query_with_gpt
from search.makeSQL import build_metadata_where_clause

# -----------------------
# 환경 변수 및 상수
# -----------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "survey")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("[WARN] OPENAI_API_KEY가 설정되어 있지 않습니다. GPT 호출 시 오류가 발생할 수 있습니다.")

oai = OpenAI(api_key=OPENAI_API_KEY)

# SentenceTransformer 모델 로드 (KURE-v1 encoder)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "nlpai-lab/KURE-v1")
print(f"[INFO] Loading embedding model: {EMBEDDING_MODEL_NAME}")
embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# pgvector 연산자 (코사인 거리: <=>, L2: <->)
PGVECTOR_OP = "<=>"   # L2면 '<->' 로 교체

_MULTI_SEP = re.compile(r"[;,/]+")


def get_connection():
    """PostgreSQL 연결 헬퍼"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    return conn


def embed_text(text: str) -> np.ndarray:
    """문자열을 embedding vector(np.ndarray)로 변환"""
    if not text:
        text = " "
    vec = embed_model.encode([text])[0]
    return np.array(vec, dtype=np.float32)


# -----------------------
#  보조 함수들
# -----------------------

def _normalize_whitespace(s: str) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def _decode_codebook_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    codebooks.codebook_data가 JSON/JSONB 형태라고 가정.
    예:
      {
        "answers": [
          {"qi_val": "1", "qi_title": "제철과일(수박, 참외 등)"},
          ...
        ],
        "q_title": "여러분의 여름철 최애 간식은 무엇인가요?",
        ...
      }
    """
    data = row.get("codebook_data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {}
    elif not isinstance(data, dict):
        return {}
    return data or {}


def _extract_choices_map(codebook_data: Dict[str, Any]) -> Dict[str, str]:
    """
    codebook_data 안에서 객관식 선택지를 찾아 {value -> 라벨} 매핑을 만든다.

    지원 형태:
    - "choices": [{ "value": "1", "label": "..." }, ...]
    - "answers": [{ "qi_val": "1", "qi_title": "..." }, ...]   ← 네가 준 구조
    """
    choices = codebook_data.get("choices") or codebook_data.get("answers")
    if not isinstance(choices, list):
        return {}

    m: Dict[str, str] = {}
    for it in choices:
        if not isinstance(it, dict):
            continue
        key = str(
            it.get("qi_val")
            or it.get("q_val")
            or it.get("value")
            or it.get("code")
            or ""
        ).strip()

        val = (
            it.get("qi_title")
            or it.get("label")
            or it.get("text")
            or it.get("name")
            or ""
        ).strip()

        if key and val:
            m[key] = val
    return m


def _translate_answer_value(raw_value: str, choice_map: dict) -> str:
    """
    "1,2,5" -> "제철과일(수박, 참외 등), 아이스크림, 기타" 처럼
    qi_val 대신 qi_title/label을 사용하도록 변환.
    """
    if raw_value is None:
        return ""
    if not choice_map:
        return str(raw_value)

    parts = [p for p in _MULTI_SEP.split(str(raw_value)) if p.strip()]
    seen = set()
    labels = []
    for p in parts:
        key = p.strip()
        if key in seen:
            continue
        seen.add(key)
        labels.append(choice_map.get(key, key))
    return ", ".join(labels)


# -----------------------
#  하이브리드 RAG 메인 함수
# -----------------------

def hybrid_answer(
    user_query: str,
    k_codebooks: int = 1,              # 관련 질문 상위 1개만 선택 (정확도 ↑)
    k_answers: Optional[int] = None,   # None이면 LIMIT 없이 전체 사용
    topn_return: int = 10,
) -> Dict[str, Any]:
    """
    하이브리드 RAG 파이프라인
    - 자연어 질의 → (filters, semantic_query) 파싱
    - filters로 metadata에서 mb_sn 후보군 필터
    - semantic_query 임베딩으로 codebooks에서 question_id 후보군 검색
    - answers에서 (mb_sn ∈ 후보군, question_id ∈ 후보군)을 교차하여 답변 샘플 수집
    - GPT로 최종 요약(answer) 생성

    k_answers:
      - int 값이면 answers에서 LIMIT k_answers
      - None 이면 LIMIT 없이 전체(필터된) answers 사용
    """
    print("=" * 70)
    print(f"[Hybrid RAG] 사용자 질문: {user_query}")
    print("=" * 70)

    # 0) 파싱
    parsed = parse_query_with_gpt(user_query)
    filters = parsed.get("filters", []) or []
    semantic_query = parsed.get("semantic_query", "") or ""

    print("\n[1단계] 자연어 쿼리 파싱 결과")
    print("  - Filters:")
    for f in filters:
        print(f"    * {f}")
    print(f"  - Semantic Query: {semantic_query!r}")

    # 1) 의미 검색용 쿼리가 비어있으면 원문 전체 사용
    if not semantic_query.strip():
        semantic_query = user_query
        print("  [주의] semantic_query가 비어 있어 원문 전체를 의미 검색어로 사용합니다.")

    # 2) 의미 쿼리 임베딩
    print("\n[2단계] 의미 쿼리 임베딩 생성 중...")
    q_vec = embed_text(semantic_query)
    print("  - 임베딩 벡터 차원:", q_vec.shape)

    # 3) DB 연결
    conn = get_connection()
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 3-1) metadata 필터 + mb_sn 화이트리스트
        where_sql, where_params = build_metadata_where_clause(filters, table_name="metadata")
        sql_metadata = f"""
            SELECT mb_sn
            FROM metadata
            {where_sql}
        """
        print("\n[3단계] metadata 필터링 SQL:")
        print("  -", sql_metadata.replace("\n", " "))
        print("  - params:", where_params)

        cur.execute(sql_metadata, where_params)
        mb_rows = cur.fetchall()
        mb_list = [r["mb_sn"] for r in mb_rows if r.get("mb_sn")]
        mb_set = set(mb_list)

        print(f"  - 필터링된 응답자 수: {len(mb_set)}명")

        # 3-2) codebooks에서 question_id 후보군 검색
        print("\n[4단계] codebooks에서 질문 후보군 검색 중...")
        sql_codebooks = f"""
            SELECT codebook_id AS question_id,
                   codebook_data,
                   (q_vector {PGVECTOR_OP} %s::vector) AS distance
            FROM codebooks
            ORDER BY q_vector {PGVECTOR_OP} %s::vector
            LIMIT %s;
        """
        params_cb = (q_vec.tolist(), q_vec.tolist(), k_codebooks)
        cur.execute(sql_codebooks, params_cb)
        cb_rows = cur.fetchall()

        question_ids: List[str] = []
        codebook_map: Dict[str, Dict[str, Any]] = {}
        for row in cb_rows:
            qid = row["question_id"]
            question_ids.append(qid)
            codebook_map[qid] = row

        print(f"  - 선택된 question_id 후보 {len(question_ids)}개:", question_ids)

        if not question_ids:
            print("  [경고] 의미 검색으로 매칭된 question_id가 없습니다.")
            return {
                "answer": "해당 질문과 직접적으로 매칭되는 문항을 찾지 못했습니다.",
                "filters": filters,
                "semantic_query": semantic_query,
                "question_ids": [],
                "samples": [],
                "statistics": {
                    "total_respondents": 0,
                    "analyzed_respondents": 0,
                    "total_answers": 0,
                    "analyzed_answers": 0,
                    "value_counts": {},
                },
            }

        # 3-3) answers에서 교차 필터링 + 시맨틱 정렬
        print("\n[5단계] answers에서 교차 필터링 + 시맨틱 정렬")

        sql_select_base = f"""
            SELECT
                a.mb_sn,
                a.question_id,
                a.answer_value,
                (a.a_vector {PGVECTOR_OP} %s::vector) AS distance
            FROM answers a
        """

        # k_answers 가 None 이면 LIMIT 없이 전체 사용
        if k_answers is not None:
            sql_order_clause = f"""
                ORDER BY a.a_vector {PGVECTOR_OP} %s::vector
                LIMIT %s
            """
        else:
            sql_order_clause = f"""
                ORDER BY a.a_vector {PGVECTOR_OP} %s::vector
            """

        if mb_set:
            sql_answers = f"""
                {sql_select_base}
                WHERE a.mb_sn = ANY(%s)
                  AND a.question_id = ANY(%s)
                {sql_order_clause};
            """
            if k_answers is not None:
                params_answers = (
                    q_vec.tolist(),
                    list(mb_set),
                    question_ids,
                    q_vec.tolist(),
                    k_answers,
                )
            else:
                params_answers = (q_vec.tolist(), list(mb_set), question_ids, q_vec.tolist())

            print("  - 쿼리 (mb_sn ∩ question_ids 교집합):")
            print("    ", sql_answers.replace("\n", " "))
            print("  - params:", "(벡터 생략, mb_sn 개수:", len(mb_set), ", qids:", question_ids, ")")
            cur.execute(sql_answers, params_answers)
        else:
            sql_answers = f"""
                {sql_select_base}
                WHERE a.question_id = ANY(%s)
                {sql_order_clause};
            """
            if k_answers is not None:
                params_answers = (q_vec.tolist(), question_ids, q_vec.tolist(), k_answers)
            else:
                params_answers = (q_vec.tolist(), question_ids, q_vec.tolist())

            print("  - 쿼리 (question_ids 시맨틱 정렬만):")
            print("    ", sql_answers.replace("\n", " "))
            print("  - params:", "(벡터 생략, qids:", question_ids, ")")
            cur.execute(sql_answers, params_answers)

        rows = cur.fetchall()
        print(f"  - 1차 검색 결과 행 수: {len(rows)}")

        # 0건이면 fallback
        if not rows:
            if mb_set:
                print("  - [시도 2] 교집합 결과 0건. 시맨틱(qids)만으로 재검색합니다.")
            else:
                print("  - [시도 1] 필터(mb_sn) 없음. 시맨틱(qids)만으로 검색합니다.")

            sql_loose = f"""
                {sql_select_base}
                WHERE a.question_id = ANY(%s)
                {sql_order_clause};
            """
            if k_answers is not None:
                params_loose = (q_vec.tolist(), question_ids, q_vec.tolist(), k_answers)
            else:
                params_loose = (q_vec.tolist(), question_ids, q_vec.tolist())

            cur.execute(sql_loose, params_loose)
            rows = cur.fetchall()
            print(f"  - 시도 2 결과 행 수: {len(rows)}")

        # 3-4) codebook_data를 이용해 answer_value 해석
        print("\n[6단계] codebook_data를 이용해서 answer_value 해석 중...")
        final_samples: List[Dict[str, Any]] = []
        seen_mb_q: set = set()
        unique_respondents: set = set()

        for r in rows:
            mb_sn = r.get("mb_sn")
            qid = r.get("question_id")
            if not mb_sn or not qid:
                continue

            key = (mb_sn, qid)
            if key in seen_mb_q:
                continue
            seen_mb_q.add(key)

            unique_respondents.add(mb_sn)

            raw_val = r.get("answer_value")
            cb_row = codebook_map.get(qid)
            if cb_row:
                cb_data = _decode_codebook_data(cb_row)
                choice_map = _extract_choices_map(cb_data)
                translated = _translate_answer_value(str(raw_val), choice_map)

                # 질문 제목: q_title / question_title / title 순으로 탐색
                question_title = (
                    cb_data.get("q_title")
                    or cb_data.get("question_title")
                    or cb_data.get("title")
                    or ""
                )
            else:
                translated = str(raw_val)
                question_title = ""

            final_samples.append(
                {
                    "mb_sn": mb_sn,
                    "question_id": qid,
                    "question_title": question_title,
                    "answer_value": raw_val,
                    "answer_value_text": translated,
                    "distance": float(r.get("distance") or 0.0),
                }
            )

        print(f"  - 정제된 샘플 수: {len(final_samples)} (중복 제거 후)")

        # 4) 통계 계산 + GPT 요약
        print("\n[7단계] GPT 요약 생성 요청")

        total_respondents = len(unique_respondents)
        print(f"  - 전체 응답자 수(이 질의에 대해 실제 응답한 수): {total_respondents}명")

        top_samples = final_samples[:topn_return]

        value_counts: Dict[str, int] = {}
        for s in final_samples:
            t = s.get("answer_value_text") or s.get("answer_value") or ""
            t_norm = _normalize_whitespace(str(t))
            if not t_norm:
                continue
            value_counts[t_norm] = value_counts.get(t_norm, 0) + 1

        sorted_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        stats_text_lines = [f"- 전체 응답자 수: {total_respondents}명"]
        for label, cnt in sorted_counts:
            ratio = (cnt / total_respondents * 100.0) if total_respondents > 0 else 0.0
            stats_text_lines.append(f"- {label}: {cnt}명 ({ratio:.1f}%)")
        stats_text = "\n".join(stats_text_lines)

        samples_text_lines = []
        for s in top_samples:
            mb_sn = s.get("mb_sn")
            qid = s.get("question_id")
            qtitle = s.get("question_title")
            aval = s.get("answer_value_text") or s.get("answer_value")
            line = f"[mb_sn={mb_sn}] ({qid}) {qtitle} -> {aval}"
            samples_text_lines.append(line)
        samples_text = "\n".join(samples_text_lines)

        summary_prompt = f"""
당신은 패널 데이터 분석 결과를 한국어로 요약하는 데이터 분석 어시스턴트입니다.

반드시 존댓말(십시오체 또는 해요체)을 사용하고,
반말(예: ~해, ~야, ~해줘)은 절대로 사용하지 마십시오.

[사용자 질문]
{user_query}

[메타데이터 필터]
{json.dumps(filters, ensure_ascii=False)}

[의미 검색용 쿼리]
{semantic_query}

[1차 통계 요약]
{stats_text}

[대표 응답 샘플 상위 {len(top_samples)}개]
{samples_text}

위 정보를 바탕으로, 사용자의 질문에 대해
1) 한두 문장으로 '결론'을 먼저 말씀해 주세요.
2) 그 다음 문단에서 주요 직무/선호/경향 등을 설명해 주세요.
3) 숫자와 비율이 중요한 경우, 가능한 범위에서 구체적인 수치를 언급해 주세요.
4) 너무 딱딱한 보고서 느낌보다는, 이해하기 쉬운 자연스러운 설명으로 작성해 주세요.
5) 모든 문장은 존댓말로 끝나도록 해 주세요.
"""
        gpt_messages = [
            {
                "role": "system",
                "content": "당신은 한국어로 패널 데이터를 요약해주는 분석 어시스턴트입니다. 항상 존댓말을 사용하십시오.",
            },
            {
                "role": "user",
                "content": summary_prompt,
            },
        ]

        gpt_resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=gpt_messages,
            temperature=0.4,
        )
        answer_text = gpt_resp.choices[0].message.content
        print("  - GPT 요약 생성 완료")

        return {
            "answer": answer_text,
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": question_ids,
            "samples": top_samples,
            "statistics": {
                "total_respondents": total_respondents,
                "analyzed_respondents": len(unique_respondents),
                "total_answers": len(rows),
                "analyzed_answers": len(final_samples),
                "value_counts": value_counts,
            },
        }

    except Exception as e:
        print("[ERROR] hybrid_answer 실행 중 오류:", repr(e))
        return {
            "answer": "질문을 분석하는 과정에서 오류가 발생했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": [],
            "samples": [],
            "statistics": {
                "total_respondents": 0,
                "analyzed_respondents": 0,
                "total_answers": 0,
                "analyzed_answers": 0,
                "value_counts": {},
            },
        }
    finally:
        cur.close()
        conn.close()


# =======================
#  스몰토크 / 대화형 유틸
# =======================

def is_smalltalk(message: str) -> bool:
    """
    인사/잡담을 대략 판별.
    ⚠️ '결혼', '자녀', '직업', '연봉', '흡연' 같은 도메인 키워드가 있으면
       무조건 데이터 질문으로 간주해서 False를 반환한다.
    """
    if not message:
        return False

    text = message.strip()
    lower = text.lower()

    # 1) 패널 설문 도메인 키워드: 이게 하나라도 있으면 절대 스몰토크 아님
    domain_keywords = [
        # 결혼/혼인
        "결혼", "혼인", "기혼", "미혼", "이혼",
        # 자녀/가족
        "자녀", "아이", "애기", "자식", "아들", "딸", "몇 명이야", "몇명이야",
        # 직업/일
        "직업", "무슨 일 하", "어떤 일 하", "직장", "직군", "직무", "하는 일",
        # 소득/연봉
        "연봉", "소득", "급여", "월급", "수입",
        # 흡연/음주
        "담배", "흡연", "피우세요", "펴?", "피세요", "술", "음주",
    ]
    if any(kw in text for kw in domain_keywords):
        return False

    # 2) 숫자나 '몇', '퍼센트' 같은 분석 키워드가 있으면 역시 데이터 질문
    if re.search(r"\d", text):
        return False
    analysis_keywords = [
        "몇", "퍼센트", "%", "비율", "통계",
        "이용", "사용", "OTT", "나이", "연령", "지역",
        "직무", "직군",
    ]
    if any(kw in text for kw in analysis_keywords):
        return False

    # 3) 전형적인 인사/잡담 패턴만 스몰토크로 취급
    greetings = [
        "안녕", "안녕하세요", "하이", "ㅎㅇ", "헬로", "hello", "hi",
        "잘 지냈", "잘 지내", "오랜만", "요즘 어때",
        "뭐해", "머해", "뭐 하고 있어",
        "고마워", "감사", "수고했어", "수고하셨",
    ]
    if any(kw in text for kw in greetings) or any(kw in lower for kw in ["hi", "hello"]):
        return True

    # 4) 아주 짧은 한두 단어이긴 해도, 도메인 키워드가 섞여있으면 데이터 질문
    if len(text) <= 5:
        if any(kw in text for kw in domain_keywords):
            return False
        return True

    return False


def smalltalk_chat(message: str, history: List[Dict[str, str]]) -> str:
    system_prompt = """
너는 패널 데이터를 분석해주는 AI이지만,
지금은 데이터 이야기 말고 가벼운 인사/잡담만 해주는 모드입니다.

- 사용자가 '안녕', '뭐해', '잘 지냈어?'처럼 말하면,
  편하게 인사하고, "데이터에 대해 궁금한 점이 있으시면 언제든지 물어봐 달라" 정도를 존댓말로 덧붙여 주세요.
- 반말(예: ~해, ~야, ~해줘)은 절대로 사용하지 마십시오.
- 항상 존댓말(해요체 또는 하십시오체)로 대답해 주세요.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
    messages.append({"role": "user", "content": message})

    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.6,
    )
    return (resp.choices[0].message.content or "").strip()


def rewrite_with_context(user_utterance: str, state: Dict[str, Any]) -> str:
    """
    직전 질문/필터/semantic_query 컨텍스트를 기반으로,
    축약된 후속 질문을 '완전히 독립적인 하나의 질문'으로 다시 써주는 함수.
    """
    last_query = state.get("last_user_query", "") or ""
    last_filters = state.get("last_filters", []) or []
    last_semantic = state.get("last_semantic_query", "") or ""

    if isinstance(last_filters, dict):
        lf_iter = [last_filters]
    else:
        lf_iter = last_filters

    filters_text = "\n".join(
        f"- {f.get('column')} {f.get('operator')} {f.get('value')}"
        for f in lf_iter
        if isinstance(f, dict)
    ) or "(이전 필터 없음)"

    system_prompt = """너는 한국어로 사용자 질문을 다시 써주는 어시스턴트입니다.

규칙:
- 이전 질문과 필터 조건, 그리고 '이전 분석 주제'를 참고해서
  이번 사용자의 발화를 '완전히 독립적인 하나의 질문'으로 다시 써 주세요.
- 사용자가 맥락만 바꾸는 말(예: '그럼 30대 남성은?', '그럼 여성은?', '서울 사는 사람은?')을 하면,
  이전 질문의 '분석 주제'(예: 결혼 여부, 자녀 수, 직업, OTT 이용 서비스 등)를 절대로 바꾸지 말고
  인구통계 조건(지역, 성별, 나이 등)만 바꿔서 한 문장으로 완성해야 합니다.
- 예시)
  이전 질문: '결혼 여부 알려줘'
  이번 발화: '30대 남성은?'
  → 다시 쓴 질문: '30대 남성의 결혼 여부는 어떻게 되나요?'
- 위와 같은 상황에서 직업 분포나 다른 완전히 새로운 주제로 바꾸면 안 됩니다.
- 만약 이번 발화가 완전히 다른 주제의 새 질문으로 보이면,
  이전 질문과 필터는 무시하고 이번 발화만으로 self-contained한 질문을 만들어 주세요.
- 출력은 오직 '다시 쓴 질문 문장' 한 줄만 반환해야 합니다.
- 설명, 따옴표, 접두사는 절대로 붙이지 마세요.
""".strip()

    user_prompt = f"""[이전 질문]
{last_query}

[이전 필터 조건]
{filters_text}

[이전 분석 주제 요약 (semantic_query)]
{last_semantic}

[이번 사용자 발화]
{user_utterance}

위 정보를 바탕으로, 이번 발화를 완전히 self-contained한 질문으로
한 문장으로 다시 써 주세요.
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
        )
        rewritten = (resp.choices[0].message.content or "").strip()
        print(f"[rewrite_with_context] '{user_utterance}' -> '{rewritten}'")
        return rewritten or user_utterance
    except Exception as e:
        print(f"[rewrite_with_context] 오류: {e!r}")
        return user_utterance


def make_chatty_answer(
    resolved_query: str,
    rag_result: Dict[str, Any],
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    hybrid_answer의 결과(rag_result)를 받아
    통계 + 샘플을 기반으로 '짧은 대화형' 설명을 생성한다.
    - 한 문단, 2~3문장 정도로만 요약
    """
    history = history or []

    stats = rag_result.get("statistics", {}) or {}
    samples = rag_result.get("samples", []) or []

    # 대표 샘플 텍스트 (혹시 GPT가 참고하고 싶을 때를 위해)
    sample_lines: List[str] = []
    for r in samples[:5]:
        if not isinstance(r, dict):
            continue
        v = r.get("answer_value_text") or r.get("answer_value")
        if v:
            sample_lines.append(f"- {v}")
    sample_text = "\n".join(sample_lines) or "(대표 응답 샘플 없음)"

    system_prompt = """너는 패널 데이터를 설명해주는 한국어 챗봇입니다.

- 반드시 존댓말(해요체 또는 하십시오체)을 사용해야 합니다.
- 반말(예: ~해, ~야, ~해줘)은 절대로 사용하지 마십시오.
- 답변은 한 문단만 사용하고, 줄바꿈(엔터)을 넣지 마십시오.
- 전체 길이는 2~3문장, 대략 2~3줄 이내로만 요약해 주세요.
- 첫 문장에는 핵심 결론(가장 많이 선택된 항목과 그 비율)을 간단히 말씀해 주세요.
- 두 번째 문장에는 주요 2~3개 선택지와 인원/비율만 간단히 덧붙여 주세요.
- 필요하다면 마지막에 "추가로 궁금한 점이 있으시면 더 물어보셔도 됩니다 :)" 한 문장을 짧게 덧붙일 수 있지만, 전체가 너무 길어지지 않도록 해 주세요.
- 불필요한 반복 설명이나 배경 설명은 최대한 줄여 주세요.
""".strip()

    user_content = f"""[사용자 질문]
{resolved_query}

[통계 요약]
{json.dumps(stats, ensure_ascii=False)}

[대표 응답 샘플 일부]
{sample_text}
""".strip()

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for h in (history[-6:] if history else []):
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
    messages.append({"role": "user", "content": user_content})

    try:
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,  # 요약은 조금 더 보수적으로
        )
        answer = (resp.choices[0].message.content or "").strip()
        print("[make_chatty_answer] 짧은 대화형 응답 생성 완료.")
        return answer
    except Exception as e:
        print(f"[make_chatty_answer] 오류: {e!r}")
        return rag_result.get(
            "answer",
            "요약을 생성하는 과정에서 오류가 발생했습니다.",
        )



def chat_with_state(
    message: str,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    상위 레벨 챗봇 진입점.

    - smalltalk(인사/잡담)은 RAG를 타지 않고 smalltalk_chat으로만 처리
    - 그 외 질의는 hybrid_answer(..., k_answers=None)로 전체 데이터 기준 분석
    - 후속 질문은 rewrite_with_context로 맥락 재구성
    """
    state = state or {}
    history: List[Dict[str, str]] = state.get("history", []) or []

    # 0) 인사/잡담 먼저 처리
    if is_smalltalk(message):
        chatty_answer = smalltalk_chat(message, history)

        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": chatty_answer},
        ]
        new_history = new_history[-10:]

        new_state: Dict[str, Any] = {
            "last_user_query": state.get("last_user_query", ""),
            "last_filters": state.get("last_filters", []),
            "last_question_ids": state.get("last_question_ids", []),
            "last_semantic_query": state.get("last_semantic_query", ""),
            "history": new_history,
        }

        return {
            "answer": chatty_answer,
            "state": new_state,
            "raw_rag_result": None,
        }

    # 1) 이전 질문이 있으면 "후속 질문"으로 보고, 맥락 기반 재작성 시도
    if state.get("last_user_query"):
        resolved_query = rewrite_with_context(message, state)
    else:
        resolved_query = message

    # 2) RAG/통계 결과 얻기 (LIMIT 해제)
    rag_result = hybrid_answer(resolved_query, k_answers=None)

    # 3) 통계 결과를 바탕으로 대화형 답변 생성
    chatty_answer = make_chatty_answer(
        resolved_query=resolved_query,
        rag_result=rag_result,
        history=history,
    )

    # 4) 다음 턴을 위한 state 업데이트
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": chatty_answer},
    ]
    new_history = new_history[-10:]

    new_state: Dict[str, Any] = {
        "last_user_query": resolved_query,
        "last_filters": rag_result.get("filters", []),
        "last_question_ids": rag_result.get("question_ids", []),
        "last_semantic_query": rag_result.get("semantic_query", ""),
        "history": new_history,
    }

    return {
        "answer": chatty_answer,
        "state": new_state,
        "raw_rag_result": rag_result,
    }


if __name__ == "__main__":
    state = None
    while True:
        q = input("질문> ").strip()
        if q in ("exit", "quit"):
            break
        res = chat_with_state(q, state)
        print("봇:", res["answer"])
        state = res["state"]


