# -*- coding: utf-8 -*-
"""
질문 쿼리 검색 파이프라인

1. 사용자 질문 쿼리 임베딩
2. q_vector와 비교하여 유사한 질문 선정
3. 필터링된 인물 중 해당 질문에 답변한 사람 선정
4. 선정된 사람들의 a_vector 반환
"""

import psycopg2
import numpy as np
import os
import torch
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv, find_dotenv

# --- .env 파일 로드 ---
load_dotenv(find_dotenv())

# --- 설정 ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

EMBEDDING_DIMENSION = 1024
TOP_K_QUESTIONS = 5  # 유사한 질문 상위 K개 선정

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
        print("[Info] DB 연결 성공")
        return conn
    except Exception as e:
        print(f"[Error] DB 연결 실패: {e}")
        return None

# --- 검색 파이프라인 ---
def search_similar_questions(conn, query_vector, top_k=TOP_K_QUESTIONS):
    """쿼리 벡터와 유사한 질문 찾기"""
    print(f"\n[Step 1] 유사한 질문 상위 {top_k}개 검색 중...")
    
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
        print(f"  - [{codebook_id}] {q_title} (유사도: {similarity:.4f})")
    
    return [row[0] for row in results]  # codebook_id 리스트 반환

def get_answers_from_respondents(conn, codebook_ids, respondent_filter=None):
    """
    선정된 질문에 답변한 사람들의 a_vector 반환
    
    Args:
        conn: DB 연결
        codebook_ids: 질문 ID 리스트
        respondent_filter: 필터링할 respondent_id 리스트 (None이면 전체)
    """
    print(f"\n[Step 2] 답변 벡터 조회 중...")
    
    cur = conn.cursor()
    
    # 필터링 조건 추가
    filter_clause = ""
    params = [tuple(codebook_ids)]
    
    if respondent_filter:
        filter_clause = "AND a.respondent_id = ANY(%s)"
        params.append(respondent_filter)
    
    query = f"""
        SELECT 
            a.answer_id,
            a.respondent_id,
            a.question_id,
            a.answer_value,
            a.a_vector,
            c.codebook_data ->> 'q_title' AS q_title
        FROM answers a
        JOIN codebooks c ON a.question_id = c.codebook_id
        WHERE a.question_id = ANY(%s)
          AND a.a_vector IS NOT NULL
          {filter_clause}
        ORDER BY a.respondent_id, a.question_id;
    """
    
    cur.execute(query, params)
    results = cur.fetchall()
    cur.close()
    
    print(f"[Result] {len(results)}개의 답변 벡터 발견")
    
    # 결과 구조화
    answer_data = []
    for row in results:
        answer_id, respondent_id, question_id, answer_value, a_vector, q_title = row
        answer_data.append({
            'answer_id': answer_id,
            'respondent_id': respondent_id,
            'question_id': question_id,
            'answer_value': answer_value,
            'a_vector': np.array(a_vector),
            'q_title': q_title
        })
    
    return answer_data

# --- 메인 검색 함수 ---
def search_pipeline(query_text, respondent_filter=None, top_k=TOP_K_QUESTIONS):
    """
    전체 검색 파이프라인
    
    Args:
        query_text: 사용자 질문 쿼리
        respondent_filter: 필터링할 respondent_id 리스트
        top_k: 유사 질문 상위 K개
    
    Returns:
        답변 데이터 리스트
    """
    print("=" * 60)
    print(f"[Query] {query_text}")
    if respondent_filter:
        print(f"[Filter] {len(respondent_filter)}명의 응답자로 필터링")
    print("=" * 60)
    
    # 1. 모델 로드 및 쿼리 임베딩
    print("\n[Step 0] 쿼리 임베딩 중...")
    model = KUREEmbeddingModel()
    query_vector = model.embed_query(query_text)
    print(f"[Result] 쿼리 벡터 생성 완료 (dim: {len(query_vector)})")
    
    # 2. DB 연결
    conn = connect_to_db()
    if not conn:
        return []
    
    try:
        # 3. 유사 질문 검색
        similar_question_ids = search_similar_questions(conn, query_vector, top_k)
        
        if not similar_question_ids:
            print("[Warning] 유사한 질문을 찾지 못했습니다.")
            return []
        
        # 4. 답변 벡터 조회
        answer_data = get_answers_from_respondents(conn, similar_question_ids, respondent_filter)
        
        print("\n" + "=" * 60)
        print(f"[Complete] 총 {len(answer_data)}개의 답변 벡터 반환")
        print("=" * 60)
        
        return answer_data
    
    finally:
        conn.close()
        print("\n[Info] DB 연결 종료")

# --- 실행 예시 ---
if __name__ == '__main__':
    # 예시 1: 전체 응답자 대상 검색
    query = "정치 성향은 어떻게 되시나요?"
    results = search_pipeline(query, top_k=3)
    
    # 예시 2: 특정 응답자만 필터링
    # filtered_respondents = [1, 2, 3, 4, 5]
    # results = search_pipeline(query, respondent_filter=filtered_respondents, top_k=3)
    
    # 결과 출력
    if results:
        print("\n[Sample Results]")
        for i, answer in enumerate(results[:5], 1):
            print(f"{i}. [응답자 {answer['respondent_id']}] {answer['q_title']}")
            print(f"   답변: {answer['answer_value']}")
            print(f"   벡터 shape: {answer['a_vector'].shape}")
