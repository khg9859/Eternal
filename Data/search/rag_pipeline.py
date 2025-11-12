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
        print(f"  - [{codebook_id}] {q_title[:50]}... (유사도: {similarity:.4f})")
    
    return [row[0] for row in results]

# --- Step 3: 답변 벡터 조회 ---
def get_answer_vectors(conn, codebook_ids, respondent_filter=None):
    """선정된 질문에 답변한 사람들의 a_vector 반환"""
    print(f"\n[Step 3] 답변 벡터 조회 중...")
    
    cur = conn.cursor()
    
    # 필터링 조건
    filter_clause = ""
    params = [codebook_ids]  # 리스트 그대로 전달
    
    if respondent_filter:
        filter_clause = "AND a.mb_sn = ANY(%s)"
        params.append(respondent_filter)
    
    query = f"""
        SELECT 
            a.answer_id,
            a.mb_sn AS respondent_id,
            a.question_id,
            a.answer_value,
            a.a_vector,
            c.codebook_data ->> 'q_title' AS q_title
        FROM answers a
        JOIN codebooks c ON a.question_id = c.codebook_id
        WHERE a.question_id = ANY(%s)
          AND a.a_vector IS NOT NULL
          {filter_clause}
        ORDER BY a.mb_sn, a.question_id;
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
            return []
        
        # Step 4: 답변 벡터 조회
        answer_data = get_answer_vectors(conn, similar_question_ids, respondent_ids)
        
        print("\n" + "=" * 70)
        print(f"[Complete] 총 {len(answer_data)}개의 답변 벡터 반환")
        print("=" * 70)
        
        return answer_data
    
    finally:
        conn.close()
        print("\n[Info] DB 연결 종료")

# --- 실행 예시 ---
if __name__ == '__main__':
    # 예시 1: 자연어 쿼리 (하이브리드 검색)
    query1 = "30대 남성들의 직업이 궁금해요"
    results1 = rag_search_pipeline(query1, top_k=3, use_gpt_parsing=True)
    
    print("\n" + "=" * 70)
    print("예시 2: 필터 없는 자연어 쿼리")
    print("=" * 70)
    
    # 예시 2: 필터 없는 자연어 쿼리
    query2 = "사람들의 결혼 여부와 자녀 수가 궁금합니다"
    results2 = rag_search_pipeline(query2, top_k=3, use_gpt_parsing=True)
    
    print("\n" + "=" * 70)
    print("[Sample Results]")
    print("=" * 70)
    if results1:
        for i, answer in enumerate(results1[:5], 1):
            print(f"{i}. [응답자 {answer['respondent_id']}] {answer['q_title'][:40]}...")
            print(f"   답변: {answer['answer_value']}")
            print(f"   벡터 shape: {answer['a_vector'].shape}")
    else:
        print("결과 없음")
    
    # 예시 2: 순수 의미 검색 (GPT 파싱 스킵)
    # query2 = "경제 만족도"
    # results2 = rag_search_pipeline(query2, top_k=5, use_gpt_parsing=False)
