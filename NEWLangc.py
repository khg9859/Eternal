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

# =========================
# ENV & GLOBAL 설정
# =========================

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

EMB_MODEL_NAME = os.getenv("EMB_MODEL_NAME", "nlpai-lab/KURE-v1")
_device = "cuda" if os.getenv("USE_CUDA", "0") == "1" else "cpu"
_embedder = SentenceTransformer(EMB_MODEL_NAME, device=_device)

PGVECTOR_OP = "<=>"   # cosine

# 너무 짧거나 잡담 같은 입력을 걸러내기 위한 기준
MIN_QUERY_CHARS = 3
CASUAL_PATTERNS = [
    "안녕", "하이", "헬로", "hi", "hello", "ㅎㅇ", "ㅎㅎ",
    "뭐해", "심심", "놀아줘", "재밌", "ㅋㅋ", "ㄷㄷ",
    "에이", "아 ", "어 ", "음", "으", "ㅇㅇ"
]

# =========================
# 1) 자연어 → filters + semantic_query
# =========================

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
    """사용자 질의를 filters / semantic_query로 분해 (gpt-4o-mini 사용)."""
    try:
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
        tool = resp.choices[0].message.tool_calls[0]
        return json.loads(tool.function.arguments)
    except Exception as e:
        print(f"[WARN] parse_query 실패, raw query를 semantic_query로 사용: {e}")
        return {"filters": [], "semantic_query": user_query}

# =========================
# 2) filters → metadata WHERE
# =========================

ALLOWED_COLS = {"gender","age","birth_year","region","mobile_carrier"}
ALLOWED_OPS  = {"=","!=","LIKE",">",">=","<","<="}

def build_where(filters: List[Dict[str,str]]) -> Tuple[str, list]:
    """filters 리스트를 SQL WHERE 절과 파라미터 리스트로 변환."""
    if not filters:
        return "", []
    conds, params = [], []
    for f in filters:
        c, op, v = f["column"], f["operator"], f["value"]
        if c not in ALLOWED_COLS or op not in ALLOWED_OPS:
            continue
        conds.append(f"{c} {op} %s")
        params.append(v)
    return (" WHERE " + " AND ".join(conds), params) if conds else ("", [])

# =========================
# DB & 벡터 유틸
# =========================

def db_conn():
    """PostgreSQL 연결 반환."""
    return psycopg2.connect(**DB, cursor_factory=RealDictCursor)

def embed(text: str) -> np.ndarray:
    """문자열을 KURE 임베딩 벡터로 변환."""
    if not text:
        text = "general preference"
    v = _embedder.encode([text], normalize_embeddings=True)[0]
    return v.astype(np.float32)

# =========================
# (추가) 분석 주제 추출 + QID 매핑
# =========================

def extract_topic(semantic_query: str) -> str:
    """semantic_query에서 '분석 주제'만 한 단어/짧은 구로 추출."""
    prompt = f"""
아래 문장에서 '분석할 주제(what to analyze)'만 한 단어 또는 짧은 구로 추출하라.

예:
- 30대 남성의 소비 패턴 → '소비'
- 서울 20대의 취업 현황 → '취업'
- SKT 사용자들의 불만 요인 → '불만'
- 20대의 OTT 이용률 → '이용률'

문장: "{semantic_query}"
주제:
"""
    try:
        res = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return (res.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[WARN] extract_topic 실패, semantic_query 그대로 사용: {e}")
        return semantic_query

def _normalize_topic_key(text: str) -> str:
    """매핑 키 비교를 위해 주제 문자열을 정규화."""
    if not text:
        return ""
    t = text.strip()
    # 작은 따옴표/큰 따옴표 제거
    t = t.strip("'\"")
    # 공백 제거 + 소문자 (영문 대비)
    t = t.replace(" ", "").lower()
    return t

# 주제 → QIDs 매핑 테이블
RAW_TOPIC_TO_QIDS = {
    "소비": ["Q2", "Q3"],
    "소비 패턴": ["Q2", "Q3"],
    "카테고리 비중": ["Q3", "Q5"],
    "관심 분야": ["Q7", "Q8", "Q9_1"],
    "관심사": ["Q7", "Q8", "Q9_1"],
    "이용률": ["Q5", "Q6"],
    "불만": ["Q12", "Q13"],
    "만족도": ["Q10", "Q11"]
}

# 정규화된 키를 사용하는 최종 매핑
TOPIC_TO_QIDS: Dict[str, List[str]] = {}
for k, v in RAW_TOPIC_TO_QIDS.items():
    TOPIC_TO_QIDS[_normalize_topic_key(k)] = v

# =========================
# Hybrid RAG Pipeline
# =========================

def hybrid_answer(
    user_query: str,
    k_questions: int = 5,
    k_answers: int = 500,
    topn_return: int = 30
) -> Dict[str, Any]:
    """
    메인 파이프라인:
    0) 입력 검증
    1) LLM 파싱 → filters / semantic_query
    2) metadata 필터로 mb_sn 후보 집합
    3) semantic_query → 주제 추출 → QID 매핑 → fallback 벡터 검색
    4) answers 교차 필터링 (QID + mb_sn + vector)
    5) 객관식 보기 라벨 적용
    6) 통계 계산 + 요약 생성
    """
    print(f"\n===== [RAG 시작] 질문: \"{user_query}\" =====")

    # 0단계: 입력 검증 (AI Summary에 부적합한 입력 걸러내기)
    q_lower = user_query.strip().lower()
    if len(q_lower) < MIN_QUERY_CHARS:
        return {
            "answer": "질문이 너무 짧습니다. 예: '서울 30대 남성의 소비 패턴을 요약해줘'처럼 조금 더 구체적으로 입력해 주세요.",
            "filters": [],
            "semantic_query": "",
            "question_ids": [],
            "samples": []
        }
    if any(pat in q_lower for pat in CASUAL_PATTERNS):
        return {
            "answer": "안녕하세요! 이 기능은 패널 데이터를 기반으로 통계를 만들어주는 AI Summary입니다.\n\n예시 질문:\n- '30대 남성의 직업 분포는?'\n- '서울 거주자의 소비 카테고리 비중 알려줘'\n- 'SKT 사용자들의 OTT 이용률 요약해줘'",
            "filters": [],
            "semantic_query": "",
            "question_ids": [],
            "samples": []
        }

    # 1단계: LLM 파싱
    parsed = parse_query(user_query)
    filters = parsed.get("filters", [])
    semantic_query = (parsed.get("semantic_query") or "").strip()
    print(f"[1단계] filters: {json.dumps(filters, ensure_ascii=False)}")
    print(f"[1단계] semantic_query: \"{semantic_query}\"")

    # semantic_query가 완전히 비어 있으면 "분석 주제 없음"으로 판단
    if not semantic_query:
        return {
            "answer": "분석할 주제가 보이지 않습니다. 예: '소비', '만족도', '이용률'처럼 알고 싶은 지표를 함께 적어주세요.",
            "filters": filters,
            "semantic_query": "",
            "question_ids": [],
            "samples": []
        }

    # 2단계: metadata filter → mb_sn 화이트리스트
    where_sql, params = build_where(filters)
    with db_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT mb_sn FROM metadata{where_sql};", params)
        mb_list = [r["mb_sn"] for r in cur.fetchall()]
    mb_set = set(mb_list)
    print(f"[2단계] 응답자 필터 결과: {len(mb_set)}명")

    # 3단계: 분석 주제 기반 QID 선택
    print("\n[3단계: 관련 질문(QID) 선택]")
    topic_raw = extract_topic(semantic_query)
    topic_norm = _normalize_topic_key(topic_raw)
    print(f"  - 추출된 주제(raw): \"{topic_raw}\" → 정규화: \"{topic_norm}\"")

    mapped_qids = TOPIC_TO_QIDS.get(topic_norm, [])

    if mapped_qids:
        print(f"  - 주제 매핑 성공 → QIDs: {mapped_qids}")
        qids = mapped_qids
    else:
        print("  - 주제 매핑 실패 → q_vector 기반 질문 검색으로 fallback.")
        q_vec_for_q = embed(semantic_query)
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT codebook_id
                FROM codebooks
                ORDER BY q_vector {PGVECTOR_OP} %s::vector
                LIMIT %s;
                """,
                (q_vec_for_q.tolist(), k_questions)
            )
            qids = [r["codebook_id"] for r in cur.fetchall()]
        print(f"  - 벡터 검색 기반 QIDs: {qids}")

    if not qids:
        return {
            "answer": "해당 주제와 관련된 질문을 찾지 못했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": [],
            "samples": []
        }

    # 4단계: answers 교차 필터링
    print("\n[4단계: answers 교차 필터링]")
    print(f"  - 필터링 대상 응답자 수: {len(mb_set)}명, QIDs: {qids}")

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
        rows: List[Dict[str, Any]] = []

        # (1) 필터(mb_sn) + QID 교집합 우선
        if mb_set:
            sql1 = f"""
                {sql_select}
                WHERE a.question_id = ANY(%s) AND a.mb_sn = ANY(%s)
                {sql_order};
            """
            cur.execute(
                sql1,
                (q_vec.tolist(), qids, list(mb_set), q_vec.tolist(), k_answers)
            )
            rows = cur.fetchall()
            print(f"  - 교집합 검색 결과: {len(rows)}건")

        # (2) 교집합 없으면 QID만으로 재검색
        if not rows:
            sql2 = f"""
                {sql_select}
                WHERE a.question_id = ANY(%s)
                {sql_order};
            """
            cur.execute(
                sql2,
                (q_vec.tolist(), qids, q_vec.tolist(), k_answers)
            )
            rows = cur.fetchall()
            print(f"  - QID-only 검색 결과: {len(rows)}건")

    if not rows:
        return {
            "answer": "조건에 맞는 응답을 찾지 못했습니다.",
            "filters": filters,
            "semantic_query": semantic_query,
            "question_ids": qids,
            "samples": []
        }

    unique_resp = set(r["mb_sn"] for r in rows)
    print(f"[4단계] 최종 응답자 수: {len(unique_resp)}명, 답변 수: {len(rows)}개")

    # 5단계: 객관식 보기 라벨 적용
    def _build_choice_map(codebook_data: dict) -> dict:
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

    def _translate(raw_value, cmap):
        if raw_value is None:
            return ""
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

    # 6단계: 통계 계산 및 요약 생성
    from collections import Counter
    answer_texts = [r["answer_value_text"] for r in rows]
    counter = Counter(answer_texts)
    top_items = counter.most_common(10)

    stats_lines = []
    total_answers = len(rows)
    for value, count in top_items:
        pct = count / total_answers * 100 if total_answers > 0 else 0.0
        stats_lines.append(f"  • {value}: {count}명 ({pct:.1f}%)")
    stats_text = "\n".join(stats_lines)

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
    except Exception as e:
        print(f"[WARN] 요약 생성 실패: {e}")
        answer = "요약 생성 중 오류가 발생했습니다. (raw 통계만 사용 가능)"

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
    q = "서울 사는 30대 남성의 소비 패턴 알려줘"
    res = hybrid_answer(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))
