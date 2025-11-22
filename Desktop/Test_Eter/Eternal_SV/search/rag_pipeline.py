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
TOP_K_QUESTIONS = 1  # 가장 유사한 질문 1개만 (관련 없는 질문 제외)

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
        "unique_respondents_sample": {
            "type": "array",
            "description": "응답자 ID 샘플 (최대 10개)",
            "items": {"type": "string"}
        }
    },
    "required": ["answer_data", "total_respondents", "total_answers", "unique_respondents_sample"]
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
        print("[Step 3] 필터 없음 - 전체 응답자 대상")
        return None
    
    print(f"\n[Step 3] Metadata 필터링 중... ({len(filters)}개 조건)")
    
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

# --- Step 3: 답변 통계 조회 (최적화된 쿼리) ---
def get_answer_statistics(conn, codebook_ids, query_vector, respondent_filter=None):
    """
    선정된 질문에 답변한 사람들의 통계 정보 반환 (쿼리 최적화)
    
    최적화 전략:
    1. 벡터 유사도로 관련 답변 먼저 필터링 (선택도 낮음)
    2. 그 다음 metadata 필터 적용 (선택도 높음)
    """
    print(f"\n[Step 4] 답변 통계 조회 중 (최적화된 쿼리)...")
    
    cur = conn.cursor()
    vector_list = query_vector.tolist()
    
    if respondent_filter:
        # 최적화: metadata 필터 먼저 적용 후 벡터 유사도 정렬
        # 606명 → 5명으로 줄어드는 문제 해결
        query = f"""
            SELECT DISTINCT
                a.answer_id,
                a.mb_sn AS respondent_id,
                a.question_id,
                a.answer_value,
                c.codebook_data ->> 'q_title' AS q_title,
                c.codebook_data,
                CASE 
                    WHEN a.a_vector IS NOT NULL THEN a.a_vector <=> %s::vector
                    ELSE 999
                END AS distance
            FROM answers a
            JOIN codebooks c ON a.question_id = c.codebook_id
            WHERE a.question_id = ANY(%s)
              AND a.mb_sn = ANY(%s)
            ORDER BY distance;
        """
        params = (vector_list, codebook_ids, respondent_filter)
    else:
        # metadata 필터 없이 벡터 유사도만
        query = f"""
            SELECT DISTINCT
                a.answer_id,
                a.mb_sn AS respondent_id,
                a.question_id,
                a.answer_value,
                c.codebook_data ->> 'q_title' AS q_title,
                c.codebook_data,
                CASE 
                    WHEN a.a_vector IS NOT NULL THEN a.a_vector <=> %s::vector
                    ELSE 999
                END AS distance
            FROM answers a
            JOIN codebooks c ON a.question_id = c.codebook_id
            WHERE a.question_id = ANY(%s)
            ORDER BY distance;
        """
        params = (vector_list, codebook_ids)
    
    cur.execute(query, params)
    results = cur.fetchall()
    cur.close()
    
    print(f"[Result] {len(results)}개의 답변 발견")
    
    # 벡터 유사도 통계
    with_vector = sum(1 for r in results if r[6] < 999)
    without_vector = len(results) - with_vector
    print(f"  - a_vector 있음: {with_vector}개, 없음: {without_vector}개")
    
    # 응답자 수 계산
    unique_respondents = set()
    answer_data = []
    
    for row in results:
        answer_id, respondent_id, question_id, answer_value, q_title, codebook_data, distance = row
        
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
            'q_title': q_title,
            'distance': float(distance) if distance < 999 else None  # 벡터 유사도 거리
        })
    
    print(f"[Result] 총 {len(unique_respondents)}명의 응답자가 답변함")
    
    # 통계 계산: 답변별 분포
    answer_distribution = {}
    for answer in answer_data:
        answer_text = answer['answer_text']
        if answer_text not in answer_distribution:
            answer_distribution[answer_text] = {
                'count': 0,
                'respondents': set()
            }
        answer_distribution[answer_text]['count'] += 1
        answer_distribution[answer_text]['respondents'].add(answer['respondent_id'])
    
    # 비율 계산
    total_unique = len(unique_respondents)
    statistics = []
    for answer_text, data in answer_distribution.items():
        unique_count = len(data['respondents'])
        percentage = (unique_count / total_unique * 100) if total_unique > 0 else 0
        statistics.append({
            'answer_text': answer_text,
            'count': unique_count,
            'percentage': round(percentage, 2)
        })
    
    # 비율 높은 순으로 정렬
    statistics.sort(key=lambda x: x['percentage'], reverse=True)
    
    return {
        'answer_data': answer_data,
        'total_respondents': len(unique_respondents),
        'total_answers': len(results),
        'unique_respondents_sample': list(unique_respondents)[:10],  # 샘플 10명만
        'statistics': statistics  # 답변별 통계 추가
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
        print(f"\n[최적화] 실행 순서: 의미 검색(선택도 낮음) → Metadata 필터(선택도 높음)")
        
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
        # Step 1: 의미 검색어 임베딩 (먼저 실행)
        print(f"\n[Step 1] 의미 검색어 임베딩 중: '{semantic_query}'")
        model = KUREEmbeddingModel()
        query_vector = model.embed_query(semantic_query)
        print(f"[Result] 쿼리 벡터 생성 완료 (dim: {len(query_vector)})")
        
        # Step 2: 유사 질문 검색 (선택도 낮음 - 먼저 실행)
        similar_question_ids = search_similar_questions(conn, query_vector, top_k)
        
        if not similar_question_ids:
            print("[Warning] 유사한 질문을 찾지 못했습니다.")
            return {'answer_data': [], 'total_respondents': 0, 'total_answers': 0, 'unique_respondents': []}
        
        # Step 3: Metadata 필터링 (선택도 높음 - 나중에 실행)
        respondent_ids = filter_respondents_by_metadata(conn, filters)
        
        # Step 4: 답변 통계 조회 (최적화된 쿼리)
        # 벡터 유사도로 먼저 좁힌 후 metadata 필터 적용
        result = get_answer_statistics(conn, similar_question_ids, query_vector, respondent_ids)
        
                # Step 5: 응답자들의 나이대 분포 조회
        unique_respondents = list(set([answer['respondent_id'] for answer in result['answer_data']]))
        if unique_respondents:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN age::integer BETWEEN 20 AND 29 THEN '20대'
                        WHEN age::integer BETWEEN 30 AND 39 THEN '30대'
                        WHEN age::integer BETWEEN 40 AND 49 THEN '40대'
                        WHEN age::integer >= 50 THEN '50대'
                        ELSE '기타'
                    END as age_group,
                    COUNT(*) as count
                FROM metadata
                WHERE mb_sn = ANY(%s) AND age IS NOT NULL
                GROUP BY age_group
                ORDER BY age_group
            """, (unique_respondents,))
            
            age_data = cur.fetchall()
            total_count = sum(row[1] for row in age_data if row[0] != '기타')
            
            # 퍼센트 계산
            demographics = {}
            demographics_percent = {}
            for row in age_data:
                if row[0] != '기타':
                    age_group = row[0]
                    count = row[1]
                    percentage = round((count / total_count * 100), 2) if total_count > 0 else 0
                    demographics[age_group] = count
                    demographics_percent[age_group] = percentage
            
            result['demographics'] = demographics
            result['demographics_percent'] = demographics_percent
            print(f"[Step 5] 나이대 분포: {demographics} ({demographics_percent})")
            cur.close()
        else:
            result['demographics'] = {}
            result['demographics_percent'] = {}

        # ✅ Step 6: 지역 분포 조회 (퍼센트까지 계산)
        if unique_respondents:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    region,
                    COUNT(*) AS count
                FROM metadata
                WHERE mb_sn = ANY(%s)
                  AND region IS NOT NULL
                GROUP BY region
                ORDER BY count DESC
            """, (unique_respondents,))
            
            region_rows = cur.fetchall()
            cur.close()

            total_region = sum(row[1] for row in region_rows) if region_rows else 0

            region_distribution = {}
            region_distribution_percent = {}

            for region, count in region_rows:
                region_distribution[region] = count
                if total_region > 0:
                    pct = round(count / total_region * 100, 2)
                else:
                    pct = 0.0
                region_distribution_percent[region] = pct

            result['region_distribution'] = region_distribution
            result['region_distribution_percent'] = region_distribution_percent

            # 🔍 디버그 출력 (퍼센트 + 인원수 함께)
            print("\n[Step 6] 지역별 응답률 비중 (%):")
            for region, count in region_rows:
                pct = region_distribution_percent.get(region, 0.0)
                print(f"  - {region}: {pct}% ({count}명)")
        else:
            result['region_distribution'] = {}
            result['region_distribution_percent'] = {}


        
        print("\n" + "=" * 70)
        print(f"[Complete] 총 {result['total_respondents']}명의 응답자, {result['total_answers']}개의 답변")
        print("=" * 70)
        
        # 자연어 답변 생성
        if result['statistics']:
            total_respondents = result['total_respondents']
            answer_summary = f"{total_respondents}명의 응답자 중 "
            
            # 상위 3개
            top_stats = result['statistics'][:3]
            summary_parts = []
            top_count = 0
            
            for stat in top_stats:
                summary_parts.append(f"{stat['answer_text']} {stat['count']}명({stat['percentage']}%)")
                top_count += stat['count']
            
            # 나머지를 "기타"로 묶기
            if len(result['statistics']) > 3:
                other_count = total_respondents - top_count
                other_percentage = round((other_count / total_respondents * 100), 2) if total_respondents > 0 else 0
                summary_parts.append(f"기타 {other_count}명({other_percentage}%)")
            
            answer_summary += ", ".join(summary_parts) + "입니다."
            result['answer_summary'] = answer_summary
            print(f"\n[답변 요약] {answer_summary}")
        
        return result
    
    finally:
        conn.close()
        print("\n[Info] DB 연결 종료")

# --- 실행 예시 ---
if __name__ == '__main__':
    # 예시 1: 자연어 쿼리 (하이브리드 검색)
    query1 = "서울 거주하는 30대 남성의 직업 중 전문직인 사람"
    results1 = rag_search_pipeline(query1, top_k=1, use_gpt_parsing=True)  # top_k=1로 변경
    
    print("\n" + "=" * 70)
    print("예시 2: 필터 없는 자연어 쿼리")
    print("=" * 70)
    
    # 예시 2: 필터 없는 자연어 쿼리
    query2 = "서울 거주하는 30대 남성의 직업 중 전문직인 사람"
    results2 = rag_search_pipeline(query2, top_k=1, use_gpt_parsing=True)  # top_k=1로 변경
    
    print("\n" + "=" * 70)
    print("--- [결과 1] ---")
    print("=" * 70)
    if results1 and results1.get('answer_data'):
        # JSON 형태로 출력
        output = {
            "total_respondents": results1['total_respondents'],
            "total_answers": results1['total_answers'],
            "unique_respondents_sample": results1['unique_respondents_sample'],
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
            "unique_respondents_sample": results2['unique_respondents_sample']
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("결과 없음")
    
    # 예시 2: 순수 의미 검색 (GPT 파싱 스킵)
    # query2 = "경제 만족도"
    # results2 = rag_search_pipeline(query2, top_k=5, use_gpt_parsing=False)
