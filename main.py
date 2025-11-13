// 백엔드 연결용 FastAPI 코드
// 디렉터리는 DATA 폴더 안에 넣어서 테스트 하면 됩니다.


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Optional
import numpy as np

app = FastAPI(title="Eternel API", description="자연어 질의 기반 패널 데이터 검색 API")

# CORS 설정 (프론트엔드와 연결을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 연결 설정
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "capstone",
    "user": "postgres",
    "password": "Sjw@040107"
}

# Pydantic 모델들
class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class QuestionResponse(BaseModel):
    codebook_id: str
    q_title: str
    answers: List[dict]

class AnswerResponse(BaseModel):
    answer_id: int
    mb_sn: str
    question_id: str
    answer_value: str

class RespondentResponse(BaseModel):
    mb_sn: str
    gender: Optional[str]
    age: Optional[str]
    region: Optional[str]
    mobile_carrier: Optional[str]

def get_db_connection():
    """데이터베이스 연결을 반환합니다."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 연결 실패: {str(e)}")

@app.get("/")
async def root():
    """API 상태 확인"""
    return {"message": "Eternel API가 정상적으로 실행 중입니다!", "status": "running"}

@app.get("/health")
async def health_check():
    """헬스 체크 - 데이터베이스 연결 확인"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"헬스 체크 실패: {str(e)}")

@app.get("/stats")
async def get_stats():
    """데이터베이스 통계 정보"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 각 테이블의 레코드 수 조회
            stats = {}
            
            tables = ['respondents', 'metadata', 'codebooks', 'answers']
            for table in tables:
                cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cur.fetchone()['count']
            
            # 임베딩 벡터가 있는 레코드 수
            cur.execute("SELECT COUNT(*) as count FROM codebooks WHERE q_vector IS NOT NULL")
            stats['questions_with_vectors'] = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM answers WHERE a_vector IS NOT NULL")
            stats['answers_with_vectors'] = cur.fetchone()['count']
            
        conn.close()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@app.get("/questions", response_model=List[QuestionResponse])
async def get_questions(limit: int = 10):
    """질문 목록 조회"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT codebook_id, codebook_data 
                FROM codebooks 
                ORDER BY codebook_id 
                LIMIT %s
            """, (limit,))
            
            questions = []
            for row in cur.fetchall():
                data = row['codebook_data']
                questions.append(QuestionResponse(
                    codebook_id=row['codebook_id'],
                    q_title=data.get('q_title', ''),
                    answers=data.get('answers', [])
                ))
        
        conn.close()
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 조회 실패: {str(e)}")

@app.get("/respondents", response_model=List[RespondentResponse])
async def get_respondents(limit: int = 10):
    """응답자 목록 조회"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT r.mb_sn, m.gender, m.age, m.region, m.mobile_carrier
                FROM respondents r
                LEFT JOIN metadata m ON r.mb_sn = m.mb_sn
                ORDER BY r.mb_sn
                LIMIT %s
            """, (limit,))
            
            respondents = []
            for row in cur.fetchall():
                respondents.append(RespondentResponse(
                    mb_sn=row['mb_sn'],
                    gender=row['gender'],
                    age=row['age'],
                    region=row['region'],
                    mobile_carrier=row['mobile_carrier']
                ))
        
        conn.close()
        return respondents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"응답자 조회 실패: {str(e)}")

@app.post("/search/questions")
async def search_questions(request: SearchRequest):
    """질문 검색 (텍스트 기반)"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 간단한 텍스트 검색 (LIKE 사용)
            cur.execute("""
                SELECT codebook_id, codebook_data 
                FROM codebooks 
                WHERE codebook_data->>'q_title' ILIKE %s
                ORDER BY codebook_id
                LIMIT %s
            """, (f"%{request.query}%", request.limit))
            
            questions = []
            for row in cur.fetchall():
                data = row['codebook_data']
                questions.append({
                    "codebook_id": row['codebook_id'],
                    "q_title": data.get('q_title', ''),
                    "answers": data.get('answers', [])
                })
        
        conn.close()
        return {"query": request.query, "results": questions, "count": len(questions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 검색 실패: {str(e)}")

@app.post("/search/answers")
async def search_answers(request: SearchRequest):
    """답변 검색"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT a.answer_id, a.mb_sn, a.question_id, a.answer_value,
                       c.codebook_data->>'q_title' as question_title
                FROM answers a
                LEFT JOIN codebooks c ON a.question_id = c.codebook_id
                WHERE a.answer_value ILIKE %s
                ORDER BY a.answer_id
                LIMIT %s
            """, (f"%{request.query}%", request.limit))
            
            answers = []
            for row in cur.fetchall():
                answers.append({
                    "answer_id": row['answer_id'],
                    "mb_sn": row['mb_sn'],
                    "question_id": row['question_id'],
                    "answer_value": row['answer_value'],
                    "question_title": row['question_title']
                })
        
        conn.close()
        return {"query": request.query, "results": answers, "count": len(answers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 검색 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
