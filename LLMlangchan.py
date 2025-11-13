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
SYSTEM_PROMPT = """
너는 PostgreSQL 기반 질의 분석기다.
아래 스키마에 맞춰 사용자의 요청을 두 조각으로 분해해 JSON만 반환하라:
- filters: [{column, operator, value}]  (metadata 테이블 컬럼만 사용)
- semantic_query: string (의미 검색용 핵심 키워드/문장)

컬럼: gender('남성'/'여성'), age(INT), birth_year(INT),
      region(VARCHAR, 예:'서울', '서울특별시', '경기', '경기도 광주시' 등 시작 일치),
      mobile_carrier('SKT','KT','LGU+','Wiz')

규칙:
- "30대" → age >= 30 AND age < 40
- "1990년대생" → birth_year >= 1990 AND birth_year < 2000
- "서울" → region LIKE '서울%'
- 스키마 밖(결혼, 직업 등)은 filters에 넣지 말고 semantic_query에만 남겨라.
반드시 {"filters":[...], "semantic_query": "..."} 만 출력.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "operator": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["column", "operator", "value"]
            }
        },
        "semantic_query": {"type": "string"}
    },
    "required": ["filters", "semantic_query"]
}

def parse_query(user_query: str) -> dict:
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "extract",
                "description": "사용자 요청을 filters/semantic_query로 분해",
                "parameters": SCHEMA
            }
        }],
        tool_choice={"type": "function", "function": {"name": "extract"}},
        temperature=0.0
    )
    try:
        tool = resp.choices[0].message.tool_calls[0]
        return json.loads(tool.function.arguments)
    except Exception:
        return {"filters": [], "semantic_query": user_query}

# -----------------------
# 2) filters → metadata WHERE
# -----------------------
ALLOWED_COLS = {"gender","age","birth_year","region","mobile_carrier"}
ALLOWED_OPS  = {"=","!=","LIKE",">",">=","<","<="}

def build_where(filters: List[Dict[str,str]]) -> Tuple[str, list]:
    if not filters: return "", []
    conds, params = [], []
    for f in filters:
        c, op, v = f["column"], f["operator"], f["value"]
        if c not in ALLOWED_COLS or op not in ALLOWED_OPS:
            continue
        conds.append(f"{c} {op} %s")
        params.append(v)
    return (" WHERE " + " AND ".join(conds), params) if conds else ("", [])

# -----------------------
# 3) DB util
# -----------------------
def db_conn():
    return psycopg2.connect(**DB, cursor_factory=RealDictCursor)

# -----------------------
# 4) 벡터 유틸
# -----------------------
def embed(text: str) -> np.ndarray:
    if not text: text = "general preference"
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
        r["answer_value_text"] = _translate_answer_value(r.get("answer_value"), cmap) if cmap else r.get("answer_value")
        out.append(r)
    return out

# -----------------------
# 6) 파이프라인
# -----------------------
def hybrid_answer(user_query: str, k_questions: int = 3, k_answers: int = 50, topn_return: int = 10) -> Dict[str,Any]:
    print(f"\n{'='*25}\n[ RAG 파이프라인 시작 ]\n- 사용자 질문: \"{user_query}\"\n{'='*25}")

    # 1단계: 자연어 질의 분석 (LLM 호출)
    print("\n[ 1단계: 자연어 질의 분석 ]")
    parsed = parse_query(user_query)
    filters = parsed.get("filters", [])
    semantic_query = parsed.get("semantic_query", "").strip()
    print(f"  - 분석 결과 (Filters): {json.dumps(filters, ensure_ascii=False)}")
    print(f"  - 분석 결과 (Semantic Query): \"{semantic_query}\"")

    # 2단계: 메타데이터 필터 → mb_sn 화이트리스트
    print("\n[ 2단계: 메타데이터 필터링 ]")
    where_sql, params = build_where(filters)
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT mb_sn FROM metadata{where_sql};", params)
        mb_list = [r["mb_sn"] for r in cur.fetchall()]
    mb_set = set(mb_list)
    print(f"  - 실행된 SQL: SELECT mb_sn FROM metadata{where_sql};")
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
            (q_vec.tolist(), k_questions)
        )
        qids = [r["codebook_id"] for r in cur.fetchall()]
    print(f"  - 가장 관련성 높은 질문 ID {len(qids)}개 찾음: {qids}")

    if not qids:
        return {"answer": "관련 질문을 찾지 못했습니다.", "filters": filters, "semantic_query": semantic_query, "question_ids": [], "sources": []}

    # 4단계: answers 교차 필터 + a_vector 유사도 정렬 (+ codebooks 조인)
    print("\n[ 4단계: 하이브리드 답변 검색 ]")
    print(f"  - 검색 조건: 응답자 {len(mb_set)}명, 질문 ID {qids}")
    with db_conn() as conn, conn.cursor() as cur:
        if mb_set:
            cur.execute(
                f"""
                SELECT a.answer_id, a.mb_sn, a.question_id, a.answer_value,
                       a.a_vector {PGVECTOR_OP} %s::vector AS distance,
                       c.codebook_data
                FROM answers a
                LEFT JOIN codebooks c ON a.question_id = c.codebook_id
                WHERE a.question_id = ANY(%s) AND a.mb_sn = ANY(%s)
                ORDER BY a.a_vector {PGVECTOR_OP} %s::vector
                LIMIT %s;
                """,
                (q_vec.tolist(), qids, list(mb_set), q_vec.tolist(), k_answers)
            )
        else:
            cur.execute(
                f"""
                SELECT a.answer_id, a.mb_sn, a.question_id, a.answer_value,
                       a.a_vector {PGVECTOR_OP} %s::vector AS distance,
                       c.codebook_data
                FROM answers a
                LEFT JOIN codebooks c ON a.question_id = c.codebook_id
                WHERE a.question_id = ANY(%s)
                ORDER BY a.a_vector {PGVECTOR_OP} %s::vector
                LIMIT %s;
                """,
                (q_vec.tolist(), qids, q_vec.tolist(), k_answers)
            )
        rows = cur.fetchall()
    print(f"  - 검색된 답변 후보 수: {len(rows)}개")

    if not rows:
        return {"answer": "조건에 맞는 응답을 찾지 못했습니다.", "filters": filters, "semantic_query": semantic_query, "question_ids": qids, "sources": []}

    # 객관식 번호 → 라벨 텍스트 부착
    rows = _attach_human_readable_labels(rows)

    # 5단계: (선택) LLM 재랭킹 — 상위 topn_return 유지
    print("\n[ 5단계: LLM 재랭킹 ]")
    docs = [{"id": f"D{i:04d}",
             "text": f"[mb:{r['mb_sn']}] {r['question_id']} :: {r.get('answer_value_text') or r.get('answer_value') or ''}"} 
            for i, r in enumerate(rows)]
    context = "\n".join(f"{d['id']}: {d['text']}" for d in docs)
    print(f"  - {len(docs)}개의 답변 후보를 LLM에 전달하여 재랭킹 요청...")

    rank_prompt = f"""
다음 문서 리스트에서 사용자 질문과 가장 관련 있는 상위 {topn_return}개 문서의 ID만 JSON으로 반환하라.
형식: {{"ids": ["D0000","D0003", ...]}}

[질문]
{user_query}

[문서]
{context}
"""
    try:
        rr = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": rank_prompt}],
            temperature=0.0
        )
        text = rr.choices[0].message.content or ""
        ids = re.findall(r'D\d{4}', text)
        keep = set(ids[:topn_return]) if ids else set(d["id"] for d in docs[:topn_return])
        print(f"  - LLM이 선택한 최종 답변 ID: {sorted(list(keep))}")
    except Exception:
        keep = set(d["id"] for d in docs[:topn_return])
        print(f"  - LLM 재랭킹 실패, 유사도 상위 {topn_return}개 선택: {sorted(list(keep))}")

    final = [rows[int(d["id"][1:])] for d in docs if d["id"] in keep]

    # 6단계: 서술형 요약 생성 (filters + semantic_query + 샘플10개 종합)
    print("\n[ 6단계: LLM 요약 생성 ]")
    print(f"  - 최종 {len(final)}개 답변을 기반으로 서술형 요약 생성 요청...")

    # 응답 내용만 전달 (번호/ID 제거, 라벨 사용)
    final_text = "\n".join(f"- {r.get('answer_value_text') or r.get('answer_value') or ''}" for r in final)

    summary_prompt = f"""
당신은 데이터 분석가입니다. 아래의 조건과 응답 샘플을 참고해 사용자의 질문에 대해
**짧고 자연스러운 서술형 요약**을 작성하세요. (불필요한 설명·목록·추측은 피하세요.)

[조건]
- filters: {json.dumps(filters, ensure_ascii=False)}
- semantic_query: "{semantic_query}"

[지침]
1) 응답자 번호(ID)는 무시하고, answer_value의 내용만 분석합니다.
2) 반복되거나 유사한 표현을 묶어 핵심 경향만 서술합니다.
3) 과장 없이 사실 기반으로 한두 문단 이내로 요약합니다.
4) 휴대폰·OTT·소비 행태 등 주제가 바뀌어도 같은 원칙으로 서술하세요.

[질문]
{user_query}

[응답 샘플 10개]
{final_text}

[출력 형식]
한두 문단의 간결한 서술형 답변만 작성하세요. 번호 목록(1,2,3)은 쓰지 마세요.
"""
    try:
        summ = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2
        )
        answer = summ.choices[0].message.content
        print("  - 서술형 요약 생성 완료.")
    except Exception:
        answer = "요약 생성 중 오류가 발생했지만, 관련 응답 샘플을 반환합니다."
        print("  - 요약 생성 실패.")

    return {
        "answer": answer,
        "filters": filters,
        "semantic_query": semantic_query,
        "question_ids": qids,
        "samples": final[:topn_return]
    }

# quick manual test
if __name__ == "__main__":
    q = "서울 사는 30대 남성 중 SKT 사용자들의 경제 만족도와 불만 요인을 요약해줘"
    res = hybrid_answer(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))