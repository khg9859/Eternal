# -*- coding: utf-8 -*-
"""
하이브리드 RAG 검색 파이프라인

1. 사용자 쿼리 입력
2. GPT로 쿼리 분해 (filters + semantic_query)
3. Metadata 필터링 → respondent_ids
4. Semantic query 임베딩 → 유사 질문 검색
5. 필터링된 사람들의 답변 벡터 반환
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsing import parse_query_with_gpt
from makeSQL import build_metadata_where_clause

import psycopg2
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv, find_dotenv
import json

# --- .env 파일 로드 ---
load_dotenv(find_dotenv())

# --- 설정 ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

EMBEDDING_DIMENSION = 1024
TOP_K_QUESTIONS = 5

# --- 반환 데이터 스키마 ---
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer_data": {
            "type": "array",
            "description": "검색된 답변 데이터 배열",
            "items": {
                "type": "object",
                "properties": {
                    "answer_id": {"type": "integer", "description": "답변 고유 ID"},
                    "respondent_id": {"type": "string", "description": "응답자 ID (예: 'w243872155705518')"},
                    "question_id": {"type": "string", "description": "질문 ID (예: '42', 'w2_Q5')"},
                    "answer_value": {"type": "string", "description": "원본 답변 값 (예: '1', '2')"},
                    "answer_text": {"type": "string", "description": "사람이 읽을 수 있는 답변 텍스트 (예: '엔지니어', '의사')"},
                    "q_title": {"type": "string", "description": "질문 제목 (예: '전문직', '직업')"}
                },
                "required": ["answer_id", "respondent_id", "question_id", "answer_value", "answer_text", "q_title"]
            }
        },
        "total_respondents": {
            "type": "integer",
            "description": "총 응답자 수 (중복 제거)"
        },
        "total_answers": {
            "type": "integer",
            "description": "총 답변 개수"
        },
        "unique_respondents": {
            "type": "array",
            "description": "응답자 ID 목록",
            "items": {"type": "string"}
        }
    },
    "required": ["answer_data", "total_respondents", "total_answers", "unique_respondents"]
}

# --- 헬퍼 함수 ---
def clean_text_for_embedding(text):
    """텍스트 정제"""
    if not text:
        return ""
    return str(text).strip()

def mean_pooling(model_output, attention_mask):
    """Mean Pooling"""
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

# --- KURE 임베딩 모델 ---
class KUREEmbeddingModel:
    """KURE 임베딩 모델"""
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Info] '{self.device}' 디바이스 사용")
        
        self.tokenizer = AutoTokenizer.from_pretrained("nlpai-lab/KURE-v1")
        self.model = AutoModel.from_pretrained("nlpai-lab/KURE-v1").to(self.device)
        self.model.eval()
        print("[Info] KURE 모델 로드 완료")
    
    def embed_query(self, query_text):
        """단일 쿼리 임베딩"""
        cleaned_text = clean_text_for_embedding(query_text)
        
        encoded_input = self.tokenizer(
            [cleaned_text],
            padding=True,
            truncation=True,
            return_tensors='pt',
            max_length=512
        ).to(self.device)
        
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        
        embedding = mean_pooling(model_output, encoded_input['attention_mask'])
        return embedding.cpu().numpy()[0]

# --- DB 연결 ---
def connect_to_db():
    """PostgreSQL 연결"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"[Error] DB 연결 실패: {e}")
        return None

# --- Step 1: Metadata 필터링 ---
def filter_respondents_by_metadata(conn, filters):
    """Metadata 필터로 respondent_ids 추출"""
    if not filters:
        print("[Step 1] 필터 없음 - 전체 응답자 대상")
        return None
    
    print(f"\n[Step 1] Metadata 필터링 중... ({len(filters)}개 조건)")
    
    where_clause, params = build_metadata_where_clause(filters, table_name="metadata")
    
    if not where_clause:
        return None
    
    query = f"SELECT mb_sn FROM metadata {where_clause};"
    
    cur = conn.cursor()
    cur.execute(query, params)
    results = cur.fetchall()
    cur.close()
    
    respondent_ids = [row[0] for row in results]
    print(f"[Result] {len(respondent_ids)}명의 응답자 필터링 완료")
    
    return respondent_ids

# --- Step 2: 유사 질문 검색 ---
def search_similar_questions(conn, query_vector, top_k=TOP_K_QUESTIONS):
    """쿼리 벡터와 유사한 질문 찾기"""
    print(f"\n[Step 2] 유사한 질문 상위 {top_k}개 검색 중...")
    
    cur = conn.cursor()
    query = f"""
        SELECT 
            codebook_id,
            codebook_data ->> 'q_title' AS q_title,
            1 - (q_vector <=> %s::vector) AS similarity
        FROM codebooks
        WHERE q_vector IS NOT NULL
        ORDER BY q_vector <=> %s::vector
        LIMIT %s;
    """
    
    vector_list = query_vector.tolist()
    cur.execute(query, (vector_list, vector_list, top_k))
    results = cur.fetchall()
    cur.close()
    
    print(f"[Result] {len(results)}개의 유사 질문 발견:")
    for codebook_id, q_title, similarity in results:
        print(f"  - [{codebook_id}] {q_title[:50]}... (유사도: {similarity:.7f})")
    
    return [row[0] for row in results]

# --- Step 3: 답변 통계 조회 (벡터 제외) ---
def get_answer_statistics(conn, codebook_ids, respondent_filter=None):
    """선정된 질문에 답변한 사람들의 통계 정보 반환 (a_vector 제외)"""
    print(f"\n[Step 3] 답변 통계 조회 중...")
    
    cur = conn.cursor()
    
    # 필터링 조건
    filter_clause = ""
    params = [codebook_ids]  # 리스트 그대로 전달
    
    if respondent_filter:
        filter_clause = "AND a.mb_sn = ANY(%s)"
        params.append(respondent_filter)
    
    # a_vector 제거하고 조회
    query = f"""
        SELECT DISTINCT
            a.answer_id,
            a.mb_sn AS respondent_id,
            a.question_id,
            a.answer_value,
            c.codebook_data ->> 'q_title' AS q_title,
            c.codebook_data
        FROM answers a
        JOIN codebooks c ON a.question_id = c.codebook_id
        WHERE a.question_id = ANY(%s)
          {filter_clause}
        ORDER BY a.mb_sn, a.question_id;
    """
    
    cur.execute(query, params)
    results = cur.fetchall()
    cur.close()
    
    print(f"[Result] {len(results)}개의 답변 발견")
    
    # 응답자 수 계산
    unique_respondents = set()
    answer_data = []
    
    for row in results:
        answer_id, respondent_id, question_id, answer_value, q_title, codebook_data = row
        
        unique_respondents.add(respondent_id)
        
        # 객관식 답변인 경우 보기 텍스트 매칭
        answer_text = answer_value
        if str(answer_value).isdigit() and codebook_data:
            choices = codebook_data.get('answers', [])
            if choices:  # 객관식
                for choice in choices:
                    if str(choice.get('qi_val')).strip() == str(answer_value).strip():
                        answer_text = choice.get('qi_title', answer_value)
                        break
            else:  # 숫자형 (자녀수 등)
                answer_text = f"{q_title}: {answer_value}"
        
        answer_data.append({
            'answer_id': answer_id,
            'respondent_id': respondent_id,
            'question_id': question_id,
            'answer_value': answer_value,
            'answer_text': answer_text,  # 사람이 읽을 수 있는 텍스트
            'q_title': q_title
        })
    
    print(f"[Result] 총 {len(unique_respondents)}명의 응답자가 답변함")
    
    return {
        'answer_data': answer_data,
        'total_respondents': len(unique_respondents),
        'total_answers': len(results),
        'unique_respondents': list(unique_respondents)
    }

# --- 전체 RAG 파이프라인 ---
def rag_search_pipeline(user_query, top_k=TOP_K_QUESTIONS, use_gpt_parsing=True):
    """
    하이브리드 RAG 검색 파이프라인
    
    Args:
        user_query: 사용자 자연어 쿼리
        top_k: 유사 질문 상위 K개
        use_gpt_parsing: GPT로 쿼리 분해 여부 (False면 전체를 semantic_query로 사용)
    
    Returns:
        답변 데이터 리스트
    """
    print("=" * 70)
    print(f"[User Query] {user_query}")
    print("=" * 70)
    
    # Step 0: 쿼리 분해
    if use_gpt_parsing:
        print("\n[Step 0] GPT로 쿼리 분해 중...")
        parsed = parse_query_with_gpt(user_query)
        print(f"[Result] 분해 완료:")
        print(f"  - Filters: {json.dumps(parsed['filters'], ensure_ascii=False)}")
        print(f"  - Semantic Query: {parsed['semantic_query']}")
        
        filters = parsed['filters']
        semantic_query = parsed['semantic_query']
    else:
        print("\n[Step 0] GPT 분해 스킵 - 전체를 의미 검색어로 사용")
        filters = []
        semantic_query = user_query
    
    # 의미 검색어가 없으면 원본 쿼리 사용
    if not semantic_query or semantic_query.strip() == "":
        semantic_query = user_query
        print(f"[Warning] 의미 검색어가 비어있어 원본 쿼리 사용: {semantic_query}")
    
    # DB 연결
    conn = connect_to_db()
    if not conn:
        return []
    
    try:
        # Step 1: Metadata 필터링
        respondent_ids = filter_respondents_by_metadata(conn, filters)
        
        # Step 2: 의미 검색어 임베딩
        print(f"\n[Step 2-1] 의미 검색어 임베딩 중: '{semantic_query}'")
        model = KUREEmbeddingModel()
        query_vector = model.embed_query(semantic_query)
        print(f"[Result] 쿼리 벡터 생성 완료 (dim: {len(query_vector)})")
        
        # Step 3: 유사 질문 검색
        similar_question_ids = search_similar_questions(conn, query_vector, top_k)
        
        if not similar_question_ids:
            print("[Warning] 유사한 질문을 찾지 못했습니다.")
            return {'answer_data': [], 'total_respondents': 0, 'total_answers': 0, 'unique_respondents': []}
        
        # Step 4: 답변 통계 조회 (벡터 제외)
        result = get_answer_statistics(conn, similar_question_ids, respondent_ids)
        
        print("\n" + "=" * 70)
        print(f"[Complete] 총 {result['total_respondents']}명의 응답자, {result['total_answers']}개의 답변")
        print("=" * 70)
        
        return result
    
    finally:
        conn.close()
        print("\n[Info] DB 연결 종료")

# --- 실행 예시 ---
if __name__ == '__main__':
    # 예시 1: 자연어 쿼리 (하이브리드 검색)
    query1 = "서울 거주하는 30대 남성의 직업 중 전문직인 사람"
    results1 = rag_search_pipeline(query1, top_k=3, use_gpt_parsing=True)
    
    print("\n" + "=" * 70)
    print("예시 2: 필터 없는 자연어 쿼리")
    print("=" * 70)
    
    # 예시 2: 필터 없는 자연어 쿼리
    query2 = "서울 거주하는 30대 남성의 직업 중 전문직인 사람"
    results2 = rag_search_pipeline(query2, top_k=3, use_gpt_parsing=True)
    
    print("\n" + "=" * 70)
    print("--- [결과 1] ---")
    print("=" * 70)
    if results1 and results1.get('answer_data'):
        # JSON 형태로 출력
        output = {
            "total_respondents": results1['total_respondents'],
            "total_answers": results1['total_answers'],
            "unique_respondents_count": len(results1['unique_respondents']),
            "sample_answers": [
                {
                    "respondent_id": answer['respondent_id'],
                    "question_id": answer['question_id'],
                    "q_title": answer['q_title'],
                    "answer_value": answer['answer_value'],
                    "answer_text": answer['answer_text']
                }
                for answer in results1['answer_data'][:5]
            ]
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("결과 없음")
    
    print("\n" + "=" * 70)
    print("--- [결과 2] ---")
    print("=" * 70)
    if results2 and results2.get('answer_data'):
        output = {
            "total_respondents": results2['total_respondents'],
            "total_answers": results2['total_answers'],
            "unique_respondents_count": len(results2['unique_respondents'])
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("결과 없음")
    
    # 예시 2: 순수 의미 검색 (GPT 파싱 스킵)
    # query2 = "경제 만족도"
    # results2 = rag_search_pipeline(query2, top_k=5, use_gpt_parsing=False)
