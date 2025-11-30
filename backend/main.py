# 백엔드 연결용 FastAPI 코드
## 디렉터리는 DATA 폴더 안에 넣어서 테스트 하면 됩니다.


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Optional
import numpy as np
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

from LLMlangchan import hybrid_answer, chat_with_state
from search.rag_pipeline import rag_search_pipeline

# ai_summary import 시도
try:
    import sys
    ai_summary_path = os.path.join(os.path.dirname(__file__), 'search')
    sys.path.append(ai_summary_path)
    from ai_summary import summarize_agg_results
    print(f"[INFO] ai_summary 모듈 로드 성공: {ai_summary_path}")
except Exception as e:
    print(f"[WARNING] ai_summary 모듈 로드 실패: {e}")
    summarize_agg_results = None

app = FastAPI(title="Eternel API", description="자연어 질의 기반 패널 데이터 검색 API")

# CORS 설정 (프론트엔드와 연결을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 연결 설정
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "capstone"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "1234")
}
class RAGRequest(BaseModel):
    query: str
    session_id: Optional[str] = "web_default_session"

class ChatRequest(BaseModel):
    message: str
    state: Optional[dict] = None
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

@app.post("/rag/search")
async def rag_search(req: RAGRequest):
    """
    RAG 파이프라인 기반 검색 엔드포인트
    - query: 자연어 질의
    - session_id: 대화 세션 식별자
    - 통계 데이터 + 자연어 답변 반환
    """
    try:
        # rag_pipeline 실행
        result = rag_search_pipeline(req.query, top_k=1, use_gpt_parsing=True)
        
        # AI 요약 생성 (ai_summary.py 사용)
        ai_summary_text = result.get("answer_summary", "답변을 생성할 수 없습니다.")
        
        if summarize_agg_results:
            try:
                # rag_search_pipeline의 결과를 ai_summary에 맞는 형식으로 변환
                statistics = result.get("statistics", [])
                
                if statistics and len(statistics) > 0:
                    # value_counts 형식으로 변환
                    value_counts = {"total_responses": result.get("total_respondents", 0)}
                    for stat in statistics:
                        value_counts[stat['answer_text']] = stat['count']
                    
                    # ai_summary가 기대하는 형식으로 변환
                    agg_results = {
                        "query_results": {
                            "question_1": {
                                "q_title": statistics[0].get('q_title', '질문'),
                                "codebook_id": statistics[0].get('question_id', 'unknown'),
                                "value_counts": value_counts
                            }
                        }
                    }
                    
                    print(f"[DEBUG] AI 요약 생성 시도...")
                    ai_summary_text = summarize_agg_results(req.query, agg_results)
                    print(f"[DEBUG] AI 요약 생성 완료")
            except Exception as summary_error:
                print(f"[WARNING] AI 요약 생성 실패: {summary_error}")
                import traceback
                traceback.print_exc()
        
        # 프론트엔드에 필요한 정보를 포함하여 반환
        return {
            "query": req.query,
            "session_id": req.session_id,
            "answer": ai_summary_text,  # AI 요약 사용
            "statistics": result.get("statistics", []),
            "total_respondents": result.get("total_respondents", 0),
            "total_answers": result.get("total_answers", 0),
            "answer_data": result.get("answer_data", []),  # 전체 데이터
            "demographics": result.get("demographics", {}),  # 나이대 분포 (인원수)
            "demographics_percent": result.get("demographics_percent", {}),  # 나이대 분포 (퍼센트)
            "region_distribution": result.get("region_distribution", {}),  # 지역 분포 (인원수)
            "region_distribution_percent": result.get("region_distribution_percent", {}),  # 지역 분포 (퍼센트)
            "unique_respondents_sample": result.get("unique_respondents_sample", [])
        }
    except Exception as e:
        print(f"!!! /rag/search ENDPOINT ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"RAG 검색 실패: {str(e)}")

@app.post("/rag/chat")
async def rag_chat(req: ChatRequest):
    """
    대화형 AI 챗봇 엔드포인트
    - message + state 기반으로 chat_with_state() 호출
    - 후속 질문 처리 + 대화형 말투 생성
    """
    try:
        result = chat_with_state(req.message, req.state)

        return {
            "answer": result["answer"],        # 대화형으로 가공된 최종 답변
            "state": result["state"],          # 다음 질문 위해 프론트가 저장할 state
            "raw_rag_result": result["raw_rag_result"]  # 통계/샘플 데이터
        }

    except Exception as e:
        print("[ERROR] /rag/chat 실패:", e)
        raise HTTPException(status_code=500, detail=f"대화형 챗봇 실패: {str(e)}")


@app.post("/rag/charts")
async def rag_charts(req: RAGRequest):
    """
    차트 데이터 생성 엔드포인트
    - query: 자연어 질의
    - 패널 데이터 기반 통계 분석 결과 반환
    """
    try:
        # RAG 검색으로 관련 데이터 가져오기
        result = hybrid_answer(req.query)
        
        # 실제 데이터 분석 (현재는 더미 데이터, 추후 DB 쿼리로 교체)
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 연령대별 분포 (metadata 테이블에서)
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN age BETWEEN 20 AND 29 THEN '20대'
                        WHEN age BETWEEN 30 AND 39 THEN '30대'
                        WHEN age BETWEEN 40 AND 49 THEN '40대'
                        WHEN age >= 50 THEN '50대'
                        ELSE '기타'
                    END as age_group,
                    COUNT(*) as count
                FROM metadata
                GROUP BY age_group
                ORDER BY age_group
            """)
            age_data = cur.fetchall()
            demographics = {row['age_group']: row['count'] for row in age_data if row['age_group']}
            
            # 지역별 분포
            cur.execute("""
                SELECT region, COUNT(*) as count
                FROM metadata
                WHERE region IS NOT NULL
                GROUP BY region
                ORDER BY count DESC
                LIMIT 5
            """)
            region_data = cur.fetchall()
            category_ratio = {row['region']: row['count'] for row in region_data}
            
        conn.close()
        
        # 더미 트렌드 데이터 (실제로는 시계열 분석 필요)
        monthly_trend = {"1월": 82, "2월": 90, "3월": 96, "4월": 103, "5월": 115, "6월": 122}
        sentiment_score = {"긍정": 68, "중립": 22, "부정": 10}
        trust_index = [84, 86, 87, 89, 90, 92]
        
        return {
            "query": req.query,
            "demographics": demographics if demographics else {"20대": 24, "30대": 41, "40대": 28, "50대": 7},
            "category_ratio": category_ratio if category_ratio else {"식품": 30, "패션": 25, "IT": 20, "여가": 15, "기타": 10},
            "monthly_trend": monthly_trend,
            "sentiment_score": sentiment_score,
            "trust_index": trust_index
        }
    except Exception as e:
        print(f"!!! /rag/charts ENDPOINT ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"차트 데이터 생성 실패: {str(e)}")

@app.post("/rag/summary")
async def rag_summary(req: RAGRequest):
    """
    AI 요약 생성 엔드포인트
    - query: 자연어 질의
    - RAG 기반 요약 텍스트 반환
    """
    try:
        # RAG 검색으로 요약 생성
        result = hybrid_answer(req.query)
        
        # answer를 문장 단위로 분리 (최대 5개)
        answer = result.get("answer", "")
        sentences = [s.strip() + "." for s in answer.split(".") if s.strip()]
        
        # 최소 3개, 최대 5개 문장 반환
        summary = sentences[:5] if len(sentences) >= 3 else [
            f'"{req.query}"에 대한 분석 결과입니다.',
            answer,
            "추가 정보가 필요하시면 질문해주세요."
        ]
        
        return {
            "query": req.query,
            "summary": summary
        }
    except Exception as e:
        print(f"!!! /rag/summary ENDPOINT ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"요약 생성 실패: {str(e)}")

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
        print(f"!!! /search/questions ENDPOINT ERROR: {e}") # 오류 출력 추가
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
