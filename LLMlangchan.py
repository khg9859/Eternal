# -*- coding: utf-8 -*-
"""
Hybrid RAG (SQL + pgvector) — Schema-specific single file (주제 기반 QID 매핑 적용 버전)

추가된 기능:
1) semantic_query에서 "분석 주제" 자동 추출 (extract_topic)
2) 분석 주제 → QID 매핑 테이블 TOPIC_TO_QIDS 적용
3) 3단계: QID 매핑 우선 적용 → 없으면 기존 벡터 검색 fallback
4) 4단계: 기존 hybrid 검색은 유지 (QID 필터가 자동 반영됨)
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

PGVECTOR_OP = "<=>"   # cosine

# -----------------------
# 1) 자연어 → filters + semantic_query
# -----------------------
SYSTEM_PROMPT = """
너는 PostgreSQL 기반 질의 분석기다.
아래 스키마에 맞춰 사용자의 요청을 두 조각으로 분해해 JSON만 반환하라:
- filters: [{column, operator, value}]  (metadata 테이블 컬럼만 사용)
- semantic_query: string

컬럼: gender('남성'/'여성'), age(INT), birth_year(INT),
      region(VARCHAR), mobile_carrier('SKT','KT','LGU+','Wiz')

필터 규칙:
- "30대" → age >= 30 AND age < 40
- "1990년대생" → birth_year >= 1990 AND birth_year < 2000
- "서울" → region LIKE '서울%'
스키마 밖(직업, 취향 등)은 semantic_query에만 남겨라.

반드시 {"filters":[...], "semantic_query": "..."} 형식만 출력.
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
    except:
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
# DB util
# -----------------------
def db_conn():
    return psycopg2.connect(**DB, cursor_factory=RealDictCursor)

# -----------------------
# Vector encoder
# -----------------------
def embed(text: str) -> np.ndarray:
    if not text:
        text = "general preference"
    v = _embedder.encode([text], normalize_embeddings=True)[0]
    return v.astype(np.float32)

# -----------------------
# (추가) 분석 주제 추출 함수
# -----------------------
def extract_topic(semantic_query: str) -> str:
    prompt = f"""
        아래 문장에서 '분석할 주제(what to analyze)'만 한 단어 또는 짧은 구로 추출하라.

        예:
        - 30대 남성의 소비 패턴 → '소비'
        - 서울 20대의 취업 현황 → '취업'
        - SKT 사용자들의 불만 요인 → '불만 요인' 

    문장: "{semantic_query}"
    주제:
    """
    try:
        res = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return res.choices[0].message.content.strip()
    except:
        return semantic_query

# -----------------------
# (추가) 주제 → QIDs 매핑 테이블
# -----------------------
TOPIC_TO_QIDS = {
    "소비": ["Q2", "Q3"],
    "소비 패턴": ["Q2", "Q3"],
    "카테고리 비중": ["Q3", "Q5"],
    "관심 분야": ["Q7", "Q8", "Q9_1"],
    "관심사": ["Q7", "Q8", "Q9_1"],
    "이용률": ["Q5", "Q6"],
    "불만": ["Q12", "Q13"],
    "만족도": ["Q10", "Q11"]
}

# -----------------------
# Hybrid RAG Pipeline
# -----------------------
def hybrid_answer(user_query: str,
                   k_questions: int = 5,
                   k_answers: int = 500,
                   topn_return: int = 30) -> Dict[str,Any]:

    print(f"\n===== [RAG 시작] 질문: \"{user_query}\" =====")

    # ---------------- 1단계: LLM 파싱 ----------------
    parsed = parse_query(user_query)
    filters = parsed.get("filters", [])
    semantic_query = parsed.get("semantic_query", "").strip()

    # ---------------- 2단계: metadata filter → mb_sn ----------------
    where_sql, params = build_where(filters)
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT mb_sn FROM metadata{where_sql};", params)
        mb_list = [r["mb_sn"] for r in cur.fetchall()]
    mb_set = set(mb_list)

    # ================================================================
    # 🔥 3단계: 분석 주제 기반 QID 매핑 적용 (여기가 새로 교체된 부분)
    # ================================================================
    print("\n[ 3단계: 관련 질문(QID) 선택 ]")

    # 3-A) 주제 추출
    topic = extract_topic(semantic_query)
    print(f"  - 분석 주제: {topic}")

    # 3-B) 매핑 우선 적용
    mapped_qids = TOPIC_TO_QIDS.get(topic, [])

    if mapped_qids:
        print(f"  - 주제 기반 매핑된 QIDs 사용: {mapped_qids}")
        qids = mapped_qids
    else:
        # fallback: 기존 q_vector 기반 검색
        print("  - 매핑된 주제가 없음 → 벡터 기반 질문 검색 실행.")
        q_vec = embed(semantic_query)

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

    print(f"  - 최종 선택된 QID 목록: {qids}")

    if not qids:
        return {
            "answer": "해당 주제와 관련된 질문을 찾지 못했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": [],
            "samples": []
        }

    # =================================================================
    # 🔥 4단계: answers 교차 필터링 (QID + mb_sn + vector)
    #     ※ 기존 SQL 그대로 사용해도 QIDs가 자동 반영됨.
    # =================================================================
    print("\n[ 4단계: answers 교차 필터링 ]")
    print(f"  - 필터링 대상 응답자 수: {len(mb_set)}명")

    q_vec = embed(semantic_query)

    sql_select = f"""
        SELECT a.answer_id, a.mb_sn, a.question_id, a.answer_value,
               a.a_vector {PGVECTOR_OP} %s::vector AS distance,
               c.codebook_data
        FROM answers a
        LEFT JOIN codebooks c ON a.question_id = c.codebook_id
    """
    sql_order = f"""
        ORDER BY a.a_vector {PGVECTOR_OP} %s::vector
        LIMIT %s
    """

    with db_conn() as conn, conn.cursor() as cur:
        rows = []

        if mb_set:
            sql1 = f"""
                {sql_select}
                WHERE a.question_id = ANY(%s) AND a.mb_sn = ANY(%s)
                {sql_order};
            """
            cur.execute(sql1,
                        (q_vec.tolist(), qids, list(mb_set),
                         q_vec.tolist(), k_answers))
            rows = cur.fetchall()

        if not rows:
            sql2 = f"""
                {sql_select}
                WHERE a.question_id = ANY(%s)
                {sql_order};
            """
            cur.execute(sql2,
                        (q_vec.tolist(), qids,
                         q_vec.tolist(), k_answers))
            rows = cur.fetchall()

    if not rows:
        return {
            "answer": "조건에 맞는 응답을 찾지 못했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": qids,
            "samples": []
        }

    # ================================================================
    # 이후 과정(정규화, 요약, 통계)은 기존 코드 그대로 유지
    # ================================================================
    unique_resp = set(r['mb_sn'] for r in rows)

    # (이하 원래 너의 코드 그대로)
    # ---------------------------------------------------------------
    # 객관식 보기를 라벨로 변환
    def _build_choice_map(codebook_data: dict) -> dict:
        m = {}
        if not codebook_data:
            return m
        items = codebook_data.get("answers") or []
        for it in items:
            if not isinstance(it, dict): continue
            key = str(it.get("qi_val") or it.get("q_val") or it.get("value") or "").strip()
            val = (it.get("qi_title") or it.get("label") or it.get("text") or it.get("name") or "").strip()
            if key and val: m[key] = val
        return m

    def _translate(raw_value, cmap):
        if raw_value is None: return ""
        parts = [p for p in re.split(r"[,\s]+", str(raw_value).strip()) if p]
        out = []
        used = set()
        for p in parts:
            label = cmap.get(p, p)
            if label not in used:
                used.add(label)
                out.append(label)
        return ", ".join(out)

    for r in rows:
        cmap = _build_choice_map(r.get("codebook_data"))
        if cmap:
            r["answer_value_text"] = _translate(r.get("answer_value"), cmap)
        else:
            r["answer_value_text"] = r.get("answer_value")

    # --------------------- 통계 계산 ---------------------
    from collections import Counter
    answer_texts = [r["answer_value_text"] for r in rows]
    counter = Counter(answer_texts)
    top_items = counter.most_common(10)

    stats_text = "\n".join(
        [f"  • {v}: {c}명 ({c/len(rows)*100:.1f}%)" for v,c in top_items]
    )

    final_text = "\n".join(f"- {t}" for t in answer_texts)

    summary_prompt = f"""
당신은 데이터 분석가입니다.
아래 조건과 답변 분포를 바탕으로 구체적 수치가 포함된 분석 보고서를 작성하십시오.

[필터]
{json.dumps(filters, ensure_ascii=False)}

[주제]
{semantic_query}

[QID 목록]
{qids}

[통계]
{stats_text}

[응답 샘플]
{final_text}
"""

    try:
        summary = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2
        )
        answer = summary.choices[0].message.content
    except:
        answer = "요약 생성 오류 발생"

    return {
        "answer": answer,
        "filters": filters,
        "semantic_query": semantic_query,
        "question_ids": qids,
        "samples": rows[:topn_return],
        "statistics": {
            "total_respondents": len(unique_resp),
            "total_answers": len(rows)
        }
    }

# quick test
if __name__ == "__main__":
    q = "서울 사는 30대 남성 소비 패턴 알려줘"
    res = hybrid_answer(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))
