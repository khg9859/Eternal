# -*- coding: utf-8 -*-
import os, re, json
from uuid import uuid4
from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Any, Tuple
from datetime import date
import copy 

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, session 
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

# =================================================================
# 0) 환경 및 전역 설정
# =================================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

# --- DB/API 설정 (기존 서버 파일 내용 유지) ---
DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "mydb"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "7302"),
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL     = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL    = os.getenv("EMBED_MODEL", "nlpai-lab/KURE-v1") 

OOS_WORDS = ["날씨","주가","환율","뉴스","교통","시간","주소","택배"]

app = Flask(__name__)
CORS(app)
# 대화 기록 관리를 위해 Flask Secret Key 설정 (필수)
app.secret_key = os.urandom(24) 

# --- 대화 기록 (History) 저장소 (임시) ---
# 실제 환경에서는 Redis, DB 등으로 대체해야 합니다.
CONVERSATION_HISTORY: Dict[str, List[Dict[str, str]]] = {} 

# =================================================================
# 1) DB 연결 및 쿼리 함수 (기존 로직 유지)
# =================================================================

def get_conn():
    # ... (기존 get_conn 함수 로직 유지) ...
    try:
        return psycopg2.connect(**DB)
    except Exception as e:
        print(f"[DB] connection failed: {e}")
        return None

def fetch_rows(limit: int | None = None) -> List[Dict[str, Any]]:
    # ... (기존 fetch_rows 함수 로직 유지) ...
    conn = get_conn()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = 'SELECT mb_sn, "Q10", "Q11", "Q12_1", "Q12_2", profile_vector::text AS profile_vector FROM respondents'
            if limit:
                sql += " LIMIT %s"
                cur.execute(sql, (limit,))
            else:
                cur.execute(sql)
            return cur.fetchall()
    finally: conn.close()

def _make_where_and_params(filters: Dict[str, Any]) -> tuple[str, list]:
    # ... (기존 _make_where_and_params 함수 로직 유지) ...
    where, params = [], []

    g = filters.get("gender")
    if g:
        if g in ("남","여"): g = "M" if g == "남" else "F"
        where.append('"Q10" = %s')
        params.append(g)

    dec = filters.get("decade")
    if dec is not None:
        lo, hi = int(dec), int(dec)+9
        where.append('(EXTRACT(YEAR FROM CURRENT_DATE)::int - "Q11"::int BETWEEN %s AND %s)')
        params += [lo, hi]

    if filters.get("sido"):
        where.append('"Q12_1" = %s')
        params.append(filters["sido"])

    if filters.get("sigungu"):
        where.append('"Q12_2" = %s')
        params.append(filters["sigungu"])

    return (("WHERE " + " AND ".join(where)) if where else ""), params

# =================================================================
# 2) 임베딩 및 유틸리티 (기존 로직 유지)
# =================================================================

@lru_cache(maxsize=1)
def _load_embedder():
    # ... (기존 _load_embedder 함수 로직 유지) ...
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
    # ... (기존 embed_text 함수 로직 유지) ...
    model = _load_embedder()
    v = np.array(model.encode(text, normalize_embeddings=True), dtype=np.float32)
    n = np.linalg.norm(v)
    return (v / n) if n else v

def cos_sim(u: np.ndarray, v: np.ndarray) -> float:
    # ... (기존 cos_sim 함수 로직 유지) ...
    return float(np.dot(u, v))

def fetch_topk_by_cosine(query: str, k: int = 5, prelimit: int = 800) -> List[Dict[str, Any]]:
    # ... (기존 fetch_topk_by_cosine 함수 로직 유지) ...
    qv = embed_text(query)
    rows = fetch_rows(limit=prelimit)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for r in rows:
        try:
            vec = np.array(json.loads(r["profile_vector"]), dtype=np.float32)
            n = np.linalg.norm(vec)
            if n: vec = vec / n
            scored.append((cos_sim(qv, vec), r))
        except Exception:
            continue
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:k]]

def birthyear_to_age(birth: str | int) -> int | None:
    # ... (기존 birthyear_to_age 함수 로직 유지) ...
    try:
        y = int(str(birth))
        return date.today().year - y
    except Exception:
        return None

# ✨ RAG Prompt Template (대화 기록을 포함하도록 수정)
def build_prompt(question: str, ctx_rows: List[Dict[str, Any]], history: List[Dict[str, str]]) -> str:
    """
    [대화형 Prompt] 검색된 컨텍스트와 대화 기록을 모두 포함하여 최종 프롬프트를 구성합니다.
    """
    if not ctx_rows:
        ctx = "없음"
    else:
        lines = []
        for r in ctx_rows:
            # 포맷팅 로직 유지
            sex = "남성" if r.get("Q10") == "M" else ("여성" if r.get("Q10") == "F" else str(r.get("Q10")))
            age = birthyear_to_age(r.get("Q11"))
            loc = (r.get("Q12_1") or "")
            if r.get("Q12_2"): loc += f" {r.get('Q12_2')}"
            lines.append(f"- 성별={sex} | 나이={(str(age)+'세') if age is not None else '정보없음'} | 지역={loc}")
        ctx = "\n".join(lines)
    
    # ✨ 대화 기록을 프롬프트에 주입할 형식으로 변환
    history_str = "\n".join([f"{h['role'].capitalize()}: {h['content']}" for h in history])

    return f"""아래 '컨텍스트'와 '이전 대화'를 참고하여 한국어로 간결히 답하세요.
컨텍스트에 없는 내용은 '해당 정보를 찾을 수 없습니다'라고 답하십시오.
ID나 출처는 드러내지 마십시오.

[이전 대화]
{history_str}

[질문]
{question}

[컨텍스트]
{ctx}
"""

# =================================================================
# 3) OpenAI (툴콜 및 RAG 로직)
# =================================================================

client = OpenAI(api_key=OPENAI_API_KEY)

# Tool Call 관련 SYSTEM PROMPT 및 TOOLS 정의는 기존 파일 로직을 유지

SYSTEM = (
    "너는 업로드된 고객 테이블만으로 답한다. "
    "필요하면 아래 도구를 0~1회 호출해 정확한 숫자/1위 지역을 얻고, "
    "그 외 서술형은 내가 준 컨텍스트로만 답하라. "
    "ID/출처는 드러내지 말고, 간결한 한국어로 답해라."
)

TOOLS = [
    # ... (기존 TOOLS 정의 유지) ...
    {
        "type": "function",
        "function": {
            "name": "count_people",
            "description": "조건에 맞는 인원 수를 DB에서 집계한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gender":   {"type": ["string","null"], "description": "성별: '남' 또는 '여' 또는 'M'/'F'"},
                    "decade":   {"type": ["integer","null"], "description": "연령대(10의 자리): 20,30,40 ..."},
                    "sido":     {"type": ["string","null"], "description": "시/도(서울, 경기 등)"},
                    "sigungu": {"type": ["string","null"], "description": "시/군/구(성동구, 분당구 등)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "most_region",
            "description": "조건에 맞는 지역 레벨에서 '가장 많은' 1개 지역만 반환한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gender":   {"type": ["string","null"]},
                    "decade":   {"type": ["integer","null"]},
                    "sido":     {"type": ["string","null"]},
                    "sigungu": {"type": ["string","null"]},
                    "level":   {"type": "string", "enum": ["sido", "sigungu"], "description": "집계 레벨"},
                },
                "required": ["level"],
            },
        },
    },
]

# Tool Call 지원 함수들은 기존 로직 유지
def _normalize_gender(g: str | None) -> str | None:
    # ... (기존 _normalize_gender 함수 로직 유지) ...
    if not g: return None
    if g in ("남","남성","M","m"): return "M"
    if g in ("여","여성","F","f"): return "F"
    return None

def tool_count_people(args: Dict[str, Any]) -> Dict[str, Any]:
    # ... (기존 tool_count_people 함수 로직 유지) ...
    flt = {
        "gender": _normalize_gender(args.get("gender")),
        "decade": args.get("decade"),
        "sido": args.get("sido"),
        "sigungu": args.get("sigungu"),
    }
    where_sql, params = _make_where_and_params(flt)
    sql = f"SELECT COUNT(*) FROM respondents {where_sql}"
    conn = get_conn()
    if not conn: return {"ok": False, "error": "DB connection failed"}
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cnt = cur.fetchone()[0]
    return {"ok": True, "count": int(cnt), "filters": flt}

def tool_most_region(args: Dict[str, Any]) -> Dict[str, Any]:
    # ... (기존 tool_most_region 함수 로직 유지) ...
    flt = {
        "gender": _normalize_gender(args.get("gender")),
        "decade": args.get("decade"),
        "sido": args.get("sido"),
        "sigungu": args.get("sigungu"),
    }
    level = args.get("level","sido")
    group_col = '"Q12_2"' if level == "sigungu" else '"Q12_1"'
    where_sql, params = _make_where_and_params(flt)
    sql = f'''
     SELECT {group_col} AS g, COUNT(*) AS c
     FROM respondents
     {where_sql}
     GROUP BY {group_col}
     ORDER BY c DESC
     LIMIT 1
    '''
    conn = get_conn()
    if not conn: return {"ok": False, "error": "DB connection failed"}
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if not row or not row[0]: return {"ok": True, "region": None, "count": 0, "level": level, "filters": flt}
    return {"ok": True, "region": row[0], "count": int(row[1]), "level": level, "filters": flt}


# ✨ llm_answer 함수 수정 (History 적용 및 간편/대화형 분기)
def llm_answer(question: str, session_id: str | None = None, mode: str = "conv") -> str:
    """
    사용자의 질문을 받아 RAG/Tool Call 및 대화 기록을 반영하여 답변합니다.
    """
    
    # 1. History 로드 (대화형 모드일 경우)
    history = CONVERSATION_HISTORY.get(session_id, []) if mode == "conv" and session_id else []
    
    # 2. 툴콜 시도 (주로 숫자나 지역 1위 요청 시 LLM이 호출을 결정)
    messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": question}]
    
    first = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    m = first.choices[0].message

    # 3. 툴콜 처리 (있을 경우)
    if m.tool_calls:
        tool_outputs_msgs = []
        for tc in m.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            
            # Tool Call 지원 함수 분기
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

        # 도구 결과를 반영해 최종 답변 생성 (Follow-up Call)
        messages.append({"role": "assistant", "tool_calls": m.tool_calls, "content": ""})
        messages.extend(tool_outputs_msgs)
        
        follow = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.2,
            messages=messages,
        )
        final_content = follow.choices[0].message.content.strip()
        
    # 4. 툴콜이 없으면 → RAG 컨텍스트로 답변
    else:
        # RAG 검색 및 Prompt 생성
        ctx = fetch_topk_by_cosine(question, k=5)
        # History와 Context를 포함하여 Prompt 생성
        prompt = build_prompt(question, ctx, history) 
        
        final = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        final_content = final.choices[0].message.content.strip()

    # 5. History 저장 (대화형 모드일 경우)
    if mode == "conv" and session_id:
        # User 질문과 AI 답변을 History에 추가
        history_entry = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": final_content}
        ]
        if session_id not in CONVERSATION_HISTORY:
            CONVERSATION_HISTORY[session_id] = []
        
        CONVERSATION_HISTORY[session_id].extend(history_entry)
        
        # History가 너무 길어지지 않도록 관리 (선택 사항)
        MAX_HISTORY_LENGTH = 6 # 최대 3쌍의 대화만 유지
        if len(CONVERSATION_HISTORY[session_id]) > MAX_HISTORY_LENGTH:
            CONVERSATION_HISTORY[session_id] = CONVERSATION_HISTORY[session_id][-MAX_HISTORY_LENGTH:]


    return final_content

# =================================================================
# 4) API 엔드포인트 수정 (Session ID 및 Mode 받기)
# =================================================================

@app.route("/api/chat-search", methods=["POST"])
def chat_search():
    data = request.get_json() or {}
    q = (data.get("query") or "").strip()
    session_id = data.get("session_id") # ✨ Session ID 추가
    mode = data.get("mode", "conv")    # ✨ Mode (conv/simple) 추가
    
    if not q:
        return jsonify({"error": "Query is required"}), 400
        
    if not session_id:
        session_id = str(uuid4()) # ID가 없으면 임시로 생성

    if any(w in q for w in OOS_WORDS):
        return jsonify({
            "id": f"ai-{uuid4().hex}",
            "type": "ai",
            "role": "assistant",
            "content": "이 서비스는 업로드된 데이터(테이블)에 대한 질문만 답변합니다.",
            "session_id": session_id
        })

    # ✨ llm_answer 호출 시 session_id와 mode 전달
    content = llm_answer(q, session_id=session_id, mode=mode) 
    
    return jsonify({
        "id": f"ai-{uuid4().hex}",
        "type": "ai",
        "role": "assistant",
        "content": content,
        "session_id": session_id # 응답에도 session_id 포함
    })


# =================================================================
# 5) main
# =================================================================
if __name__ == "__main__":
    print(f"🔑 OPENAI_API_KEY loaded? {bool(OPENAI_API_KEY)} | .env: {ENV_PATH}")
    print(f"🧠 EMBED_MODEL: {EMBED_MODEL} | 💬 CHAT_MODEL: {CHAT_MODEL}")
    app.run(host="0.0.0.0", port=5000, debug=True)