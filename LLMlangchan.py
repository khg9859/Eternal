# -*- coding: utf-8 -*-
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
3) semantic_query 임베딩 → codebooks.q_vector와 유사도 검색해 question_id 1~N개 선택
4) answers에서 (question_id ∈ 선택집합) AND (mb_sn ∈ 화이트리스트) 교차 필터
   + a_vector와 semantic_query 임베딩 유사도로 정렬
5) (선택) gpt-4o-mini로 재랭킹 후 요약 생성
"""

import os, json, re
from typing import List, Dict, Any, Tuple
from collections import defaultdict

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

# pgvector: cosine 연산자 사용시 '<=>' (인덱스는 vector_cosine_ops)
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
# 5) 파이프라인
# -----------------------
def hybrid_answer(user_query: str, k_questions: int = 2, k_answers: int = 50, topn_return: int = 10) -> Dict[str,Any]:
    print(f"\n{'='*25}\n[ RAG 파이프라인 시작 ]\n- 사용자 질문: \"{user_query}\"\n{'='*25}")

    # 1단계: 자연어 질의 분석 (LLM 호출)
    print("\n[ 1단계: 자연어 질의 분석 ]")
    parsed = parse_query(user_query)
    filters = parsed.get("filters", [])
    semantic_query = parsed.get("semantic_query", "").strip()
    print(f"  - 분석 결과 (Filters): {json.dumps(filters, ensure_ascii=False)}")
    print(f"  - 분석 결과 (Semantic Query): \"{semantic_query}\"")

    # 5-1) 메타데이터 필터로 mb_sn 화이트리스트
    print("\n[ 2단계: 메타데이터 필터링 ]")
    where_sql, params = build_where(filters)
    mb_list = []
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT mb_sn FROM metadata{where_sql};", params)
        mb_list = [r["mb_sn"] for r in cur.fetchall()]
    mb_set = set(mb_list)
    print(f"  - 실행된 SQL: SELECT mb_sn FROM metadata{where_sql};")
    print(f"  - SQL 파라미터: {params}")
    print(f"  - 찾은 응답자 수: {len(mb_set)}명")
    if len(mb_set) > 0:
        print(f"  - 찾은 응답자 샘플: {list(mb_set)[:5]}...")

    # 5-2) semantic_query 임베딩 → codebooks.q_vector 검색해 question_id 상위 k
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

    # 5-3) answers에서 교차 필터 + a_vector 유사도 정렬
    print("\n[ 4단계: 하이브리드 답변 검색 ]")
    print(f"  - 검색 조건: 응답자 {len(mb_set)}명, 질문 ID {qids}")
    with db_conn() as conn, conn.cursor() as cur:
        if mb_set:
            cur.execute(
                f"""
                SELECT answer_id, mb_sn, question_id, answer_value,
                       a_vector {PGVECTOR_OP} %s::vector AS distance
                FROM answers
                WHERE question_id = ANY(%s) AND mb_sn = ANY(%s)
                ORDER BY a_vector {PGVECTOR_OP} %s::vector
                LIMIT %s;
                """,
                (q_vec.tolist(), qids, list(mb_set), q_vec.tolist(), k_answers)
            )
        else:
            cur.execute(
                f"""
                SELECT answer_id, mb_sn, question_id, answer_value,
                       a_vector {PGVECTOR_OP} %s::vector AS distance
                FROM answers
                WHERE question_id = ANY(%s)
                ORDER BY a_vector {PGVECTOR_OP} %s::vector
                LIMIT %s;
                """,
                (q_vec.tolist(), qids, q_vec.tolist(), k_answers)
            )
        rows = cur.fetchall()
    print(f"  - 검색된 답변 후보 수: {len(rows)}개")

    if not rows:
        return {"answer": "조건에 맞는 응답을 찾지 못했습니다.", "filters": filters, "semantic_query": semantic_query, "question_ids": qids, "sources": []}

    # 5-4) (선택) gpt-4o-mini 재랭킹: 상위 topn_return만 유지
    print("\n[ 5단계: LLM 재랭킹 ]")
    docs = [{"id": f"D{i:04d}", "text": f"[mb:{r['mb_sn']}] {r['question_id']} :: {r['answer_value']}"} for i, r in enumerate(rows)]
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
        text = rr.choices[0].message.content
        ids = re.findall(r'D\d{4}', text or "")
        keep = set(ids[:topn_return]) if ids else set(d["id"] for d in docs[:topn_return])
        print(f"  - LLM이 선택한 최종 답변 ID: {sorted(list(keep))}")
    except Exception:
        keep = set(d["id"] for d in docs[:topn_return])
        print(f"  - LLM 재랭킹 실패, 유사도 상위 {topn_return}개 선택: {sorted(list(keep))}")

    final = [rows[int(d["id"][1:])] for d in docs if d["id"] in keep]
    final_text = "\n".join(f"- mb_sn:{r['mb_sn']} | {r['question_id']} | {r['answer_value']}" for r in final)

    # 5-5) 요약 생성 (선택)
    print("\n[ 6단계: LLM 요약 생성 ]")
    print(f"  - 최종 {len(final)}개 답변을 기반으로 요약 생성 요청...")
    summary_prompt = f"""당신은 데이터 분석가입니다. 주어진 [응답 샘플]을 분석하여 사용자의 [질문]에 대한 답변을 생성해야 합니다.

[역할]
1. 응답 샘플에 나타난 활동들을 분석하고, 가장 자주 언급된 활동이 무엇인지 파악합니다.
2. 언급된 횟수를 기반으로 순위를 매겨 목록 형태로 답변을 구성합니다.
3. 분석 결과를 바탕으로 자연스러운 문장으로 요약하여 마무리합니다.
4. 샘플에 없는 내용은 절대 언급하지 마세요.

[질문]
{user_query}

[응답 샘플]
{final_text}

[답변 형식]
서울 시민들이 주로 하는 체력 관리 활동은 다음과 같습니다.

1. **(가장 많이 언급된 활동)**
2. **(두 번째로 많이 언급된 활동)**
3. **(세 번째로 많이 언급된 활동)**

종합적으로 볼 때, 많은 분들이 (활동1)과 (활동2)를 통해 체력을 관리하고 있는 것으로 보입니다.
"""
    try:
        summ = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2
        )
        answer = summ.choices[0].message.content
        print("  - 요약 생성 완료.")
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