# -*- coding: utf-8 -*-
import os, re, json
from uuid import uuid4
from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer
from openai import OpenAI

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================
# 0) 환경
# =========================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "survey_db"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "7302"),
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL     = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL    = os.getenv("EMBED_MODEL", "nlpai-lab/KURE-v1")

OOS_WORDS = ["날씨","주가","환율","뉴스","교통","시간","주소","택배"]

# 🔁 FastAPI 앱 & CORS
app = FastAPI(title="Chat Search API (FastAPI)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 1) DB / 공통
# =========================
def get_conn():
    try:
        return psycopg2.connect(**DB)
    except Exception as e:
        print(f"[DB] connection failed: {e}")
        return None

# "만 NN 세" 같은 age 텍스트에서 숫자 추출
AGE_NUM_RE = re.compile(r"만\s*(\d{1,3})\s*세")

def parse_age_from_text(txt: Optional[str]) -> Optional[int]:
    if not txt:
        return None
    m = AGE_NUM_RE.search(txt)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    # 예외: "nan" 등
    try:
        # 혹시 "NN 세"만 있을 수도 있음
        n = int(re.findall(r"\d{1,3}", txt)[-1])
        return n
    except Exception:
        return None

def normalize_gender_kor(g: Optional[str]) -> Optional[str]:
    if not g:
        return None
    g = g.strip().lower()
    if g in ("m", "male", "남", "남성"):
        return "남성"
    if g in ("f", "female", "여", "여성"):
        return "여성"
    return None

# =========================
# 2) 컨텍스트(Top-K) - respondents.profile_vector + metadata 조인
# =========================
def fetch_rows_for_rag(prelimit: int = 800) -> List[Dict[str, Any]]:
    """
    respondents.profile_vector를 읽고, metadata에서 성별/나이텍스트/지역을 가져온다.
    """
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
            SELECT r.mb_sn,
                   r.profile_vector::text AS profile_vector,
                   m.gender AS gender_text,
                   m.age    AS age_text,
                   m.region AS region_text
            FROM respondents r
            LEFT JOIN metadata m ON m.mb_sn = r.mb_sn
            LIMIT %s
            """
            cur.execute(sql, (prelimit,))
            return cur.fetchall()
    finally:
        conn.close()

@lru_cache(maxsize=1)
def _load_embedder():
    print(f"[EMBED] loading: {EMBED_MODEL}")
    try:
        return SentenceTransformer(EMBED_MODEL)
    except Exception as e:
        print(f"[EMBED] primary load failed: {e}")
        fb = "jhgan/ko-sroberta-multitask"
        print(f"[EMBED] fallback -> {fb}")
        return SentenceTransformer(fb)

@lru_cache(maxsize=4096)
def embed_text(text: str) -> np.ndarray:
    model = _load_embedder()
    v = np.array(model.encode(text, normalize_embeddings=True), dtype=np.float32)
    n = np.linalg.norm(v)
    return (v / n) if n else v

def cos_sim(u: np.ndarray, v: np.ndarray) -> float:
    return float(np.dot(u, v))

def fetch_topk_by_cosine(query: str, k: int = 5, prelimit: int = 800) -> List[Dict[str, Any]]:
    qv = embed_text(query)
    rows = fetch_rows_for_rag(prelimit=prelimit)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for r in rows:
        try:
            vec = np.array(json.loads(r["profile_vector"]), dtype=np.float32)
            n = np.linalg.norm(vec)
            if n:
                vec = vec / n
            scored.append((cos_sim(qv, vec), r))
        except Exception:
            continue
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:k]]

def build_prompt(question: str, ctx_rows: List[Dict[str, Any]]) -> str:
    if not ctx_rows:
        ctx = "없음"
    else:
        lines = []
        for r in ctx_rows:
            sex = r.get("gender_text") or "정보없음"
            # age_text에서 숫자만 추출해 예쁘게 표시
            age_num = parse_age_from_text(r.get("age_text"))
            age_disp = f"{age_num}세" if age_num is not None else (r.get("age_text") or "정보없음")
            region = r.get("region_text") or "정보없음"
            lines.append(f"- 성별={sex} | 나이={age_disp} | 지역={region}")
        ctx = "\n".join(lines)

    return f"""아래 '컨텍스트'만 사용해 한국어로 간결히 답하세요.
컨텍스트에 없는 내용은 '해당 정보를 찾을 수 없습니다'라고 답하십시오.
ID나 출처는 드러내지 마십시오.

[질문]
{question}

[컨텍스트]
{ctx}
"""

# =========================
# 3) OpenAI & 툴콜(집계는 metadata에서)
# =========================
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM = (
    "너는 업로드된 고객 테이블만으로 답한다. "
    "필요하면 아래 도구를 0~1회 호출해 정확한 숫자/1위 지역을 얻고, "
    "그 외 서술형은 내가 준 컨텍스트로만 답하라. "
    "ID/출처는 드러내지 말고, 간결한 한국어로 답해라."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "count_people",
            "description": "조건에 맞는 인원 수(metadata 기반)를 집계한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gender":  {"type": ["string","null"], "description": "성별: 남/여/M/F"},
                    "decade":  {"type": ["integer","null"], "description": "연령대(10의 자리): 20,30,40 ..."},
                    "region":  {"type": ["string","null"], "description": "예: 서울, 경기, 부산 ..."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "most_region",
            "description": "조건에 맞는 사람들 중 가장 많은 지역 1개(metadata.region).",
            "parameters": {
                "type": "object",
                "properties": {
                    "gender": {"type": ["string","null"]},
                    "decade": {"type": ["integer","null"]},
                },
                "required": [],
            },
        },
    },
]

def _where_for_metadata(filters: Dict[str, Any]) -> tuple[str, list]:
    """metadata 테이블 전용 WHERE 생성 (gender/decade/region)"""
    where, params = [], []

    g = normalize_gender_kor(filters.get("gender"))
    if g:
        where.append("m.gender = %s")
        params.append(g)

    dec = filters.get("decade")
    if dec is not None:
        lo, hi = int(dec), int(dec) + 9
        # age_text에서 '만 NN 세' 파싱 후 between
        where.append("""
          CASE
            WHEN m.age IS NULL THEN NULL
            ELSE
              (REGEXP_REPLACE(m.age, '.*만\\s*(\\d{1,3})\\s*세.*', '\\1'))::int
          END BETWEEN %s AND %s
        """)
        params += [lo, hi]

    if filters.get("region"):
        where.append("m.region = %s")
        params.append(filters["region"])

    return (("WHERE " + " AND ".join([w for w in where if w.strip()])) if where else ""), params

def tool_count_people(args: Dict[str, Any]) -> Dict[str, Any]:
    flt = {
        "gender": args.get("gender"),
        "decade": args.get("decade"),
        "region": args.get("region"),
    }
    where_sql, params = _where_for_metadata(flt)
    sql = f"SELECT COUNT(*) FROM metadata m {where_sql}"
    conn = get_conn()
    if not conn:
        return {"ok": False, "error": "DB connection failed"}
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cnt = cur.fetchone()[0]
    return {"ok": True, "count": int(cnt), "filters": flt}

def tool_most_region(args: Dict[str, Any]) -> Dict[str, Any]:
    flt = {
        "gender": args.get("gender"),
        "decade": args.get("decade"),
    }
    where_sql, params = _where_for_metadata(flt)
    sql = f"""
      SELECT m.region AS g, COUNT(*) AS c
      FROM metadata m
      {where_sql}
      GROUP BY m.region
      ORDER BY c DESC NULLS LAST
      LIMIT 1
    """
    conn = get_conn()
    if not conn:
        return {"ok": False, "error": "DB connection failed"}
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if not row or not row[0]:
        return {"ok": True, "region": None, "count": 0, "filters": flt}
    return {"ok": True, "region": row[0], "count": int(row[1]), "filters": flt}

def llm_answer(question: str) -> str:
    """
    1) 툴콜 시도 (count_people / most_region)
    2) 없거나 불필요하면 RAG(top-K respondents + metadata 요약)로 답변
    """
    msg = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    first = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=msg,
        tools=TOOLS,
        tool_choice="auto",
    )
    m = first.choices[0].message

    if m.tool_calls:
        tool_outputs_msgs = []
        for tc in m.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            if name == "count_people":
                out = tool_count_people(args)
            elif name == "most_region":
                out = tool_most_region(args)
            else:
                out = {"ok": False, "error": f"unknown tool {name}"}

            tool_outputs_msgs.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(out, ensure_ascii=False),
            })

        follow = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.2,
            messages=msg + [
                {"role": "assistant", "tool_calls": m.tool_calls, "content": ""},
                *tool_outputs_msgs,
            ],
        )
        return follow.choices[0].message.content.strip()

    # RAG 경로
    ctx = fetch_topk_by_cosine(question, k=5)
    prompt = build_prompt(question, ctx)
    final = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return final.choices[0].message.content.strip()

# =========================
# 4) API
# =========================
class ChatSearchRequest(BaseModel):
    query: str

class ChatSearchResponse(BaseModel):
    id: str
    type: str
    role: str
    content: str

@app.post("/api/chat-search", response_model=ChatSearchResponse)
def chat_search(req: ChatSearchRequest):
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query is required")

    if any(w in q for w in OOS_WORDS):
        return ChatSearchResponse(
            id=f"ai-{uuid4().hex}",
            type="ai",
            role="assistant",
            content="이 서비스는 업로드된 데이터(테이블)에 대한 질문만 답변합니다."
        )

    content = llm_answer(q)
    return ChatSearchResponse(
        id=f"ai-{uuid4().hex}",
        type="ai",
        role="assistant",
        content=content
    )

# =========================
# 5) main
# =========================
if __name__ == "__main__":
    import uvicorn
    print(f"🔑 OPENAI_API_KEY loaded? {bool(OPENAI_API_KEY)} | .env: {ENV_PATH}")
    print(f"🧠 EMBED_MODEL: {EMBED_MODEL} | 💬 CHAT_MODEL: {CHAT_MODEL}")
    uvicorn.run("fastapi_server:app", host="0.0.0.0", port=5000, reload=True)
