# -*- coding: utf-8 -*-
"""
Q-Vector 검색 정확도 검증 도구 (for rag_pipeline.py)

[목적]
rag_pipeline.py의 'search_similar_questions' 함수를 사용하여,
사용자 쿼리가 DB의 '질문(q_title)'과 얼마나 잘 매칭되는지 검증합니다.

[주의]
이 스크립트는 './Data/search/rag_pipeline.py' (v1) 파일을 기준으로 작성되었습니다.
"""

import sys
import os
import time

# 현재 스크립트의 위치를 경로에 추가하여 rag_pipeline.py를 import 할 수 있게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # [수정] rag_pipeline.py에서 모듈 import
    from rag_pipeline import (
        KUREEmbeddingModel, 
        connect_to_db, 
        search_similar_questions
    )
except ImportError:
    print("XXX [오류] 'rag_pipeline.py'를 찾을 수 없습니다.")
    print("XXX 이 파일이 'Data/search/' 폴더 내에 있는지 확인하세요.")
    exit(1)

# --- 설정 ---
# 검증용 설정 (v1 코드에는 Threshold가 없으므로 여기서 정의)
VALIDATION_TOP_K = 10
TARGET_THRESHOLD = 0.6  # 검증 통과 기준 점수 (0.6 이상이면 PASS)

def print_search_results(query, results):
    """검색 결과 출력 헬퍼"""
    print(f"\n🔍 Query: '{query}'")
    print("-" * 60)
    
    if not results:
        print("   [결과 없음] 매칭되는 질문이 없습니다.")
        return

    # rag_pipeline.py v1은 threshold 기능이 없으므로 상위 K개를 모두 가져옴
    for rank, (codebook_id, q_title, similarity) in enumerate(results, 1):
        # 임계값 통과 여부 표시 (시각적 확인용)
        pass_fail = "✅ PASS" if similarity >= TARGET_THRESHOLD else "❌ FAIL (Low Score)"
        
        # 유사도에 따른 막대 그래프 시각화
        bar_len = int(similarity * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        
        print(f" {rank}. [{pass_fail}] {bar} {similarity:.4f}")
        print(f"    ID: {codebook_id}")
        print(f"    Q : {q_title}")
        print("-" * 60)

def run_interactive_mode(model, conn):
    """사용자 입력을 받아 실시간 검증"""
    print("\n🔵 [모드 1] 인터랙티브 검증 모드 (종료하려면 'q' 입력)")
    print(f"   * 검증 통과 기준(Threshold): {TARGET_THRESHOLD}")
    
    while True:
        user_query = input("\n검색할 질문을 입력하세요: ").strip()
        if user_query.lower() in ['q', 'quit', 'exit']:
            break
        if not user_query:
            continue

        # 임베딩
        start_time = time.time()
        query_vector = model.embed_query(user_query)
        
        # 검색 (v1 함수 호출: threshold 파라미터 없음)
        results = search_similar_questions(conn, query_vector, top_k=VALIDATION_TOP_K)
        
        end_time = time.time()
        print(f"   (소요시간: {end_time - start_time:.4f}초)")
        
        print_search_results(user_query, results)

def run_batch_mode(model, conn):
    """미리 정의된 테스트 케이스 검증"""
    print("\n🔵 [모드 2] 배치 테스트 모드")
    
    # [테스트 케이스 정의]
    # (쿼리, 기대하는 키워드가 포함된 질문 제목)
    test_cases = [
        ("결혼 했어?", "결혼"),
        ("자녀가 몇 명이야?", "자녀"),
        ("스트레스 푸는 방법", "스트레스"),
        ("무슨 일 하세요?", "직업"),
        ("연봉이 얼마야?", "소득"),
        ("학력이 어떻게 돼?", "학력"),
        ("종교가 있니?", "종교"),
        ("흡연 하시나요?", "흡연"),
        ("똥이랑 관련된 일", "직무"), # 실패 가능성 높은 케이스
    ]
    
    for query, expected_keyword in test_cases:
        query_vector = model.embed_query(query)
        
        # v1 함수 호출
        results = search_similar_questions(conn, query_vector, top_k=5)
        
        # 결과 분석
        print(f"\n📋 Test Query: '{query}' (Target: '{expected_keyword}')")
        
        found = False
        # results는 [codebook_id, q_title, similarity] 튜플 리스트라고 가정 (v1 기준 확인 필요)
        # rag_pipeline.py v1을 보면 returns [row[0] for row in results] 라고 되어있음.
        # -> 잠깐! v1 코드의 search_similar_questions는 ID 리스트만 반환합니다!
        # -> 따라서 검증을 위해 유사도 점수까지 가져오도록 코드를 약간 수정해야 하거나,
        #    이 검증 도구에서 직접 쿼리를 날려야 합니다.
        
        # [중요] rag_pipeline.py v1은 (ID, Title, Similarity)를 출력만 하고 ID 리스트만 반환합니다.
        # 검증 도구의 정확한 동작을 위해, 이 도구 내에서 직접 쿼리를 실행하는 함수를 재정의하겠습니다.
        # (기존 함수를 import해서 쓰기엔 v1의 반환값이 검증용으로 부족합니다)
        
        results = local_search_similar_questions(conn, query_vector, top_k=5)

        for i, (cid, q_title, sim) in enumerate(results):
            if expected_keyword in q_title:
                pass_mark = "✅" if sim >= TARGET_THRESHOLD else "⚠️(Low Score)"
                print(f"   -> {pass_mark} Rank {i+1}에서 발견! (유사도: {sim:.4f}) : {q_title}")
                found = True
                break
        
        if not found:
            print(f"   -> ❌ '{expected_keyword}' 관련 질문을 Top-5 내에서 찾지 못했습니다.")

# --- [보완] v1 파이프라인 함수가 ID만 반환하므로, 검증용 검색 함수를 직접 정의 ---
def local_search_similar_questions(conn, query_vector, top_k=10):
    """검증을 위해 ID, Title, Similarity를 모두 반환하는 로컬 함수"""
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
    return results

# --- 메인 실행 ---
if __name__ == "__main__":
    print("===== Q-Vector 검증 도구 (Based on rag_pipeline.py v1) =====")
    
    # 1. 모델 로드
    print("Loading KURE Model...")
    model = KUREEmbeddingModel()
    
    # 2. DB 연결
    conn = connect_to_db()
    if not conn:
        print("DB 연결 실패.")
        exit(1)

    try:
        print("\n[모드 선택]")
        print("1. 인터랙티브 모드 (직접 입력)")
        print("2. 배치 테스트 모드 (자동 검사)")
        
        choice = input("선택 (1/2): ").strip()
        
        # [수정] 검증 시에는 search_similar_questions 대신 local_search_similar_questions 사용
        # (이유: v1 파이프라인 함수가 점수를 반환하지 않음)
        
        # 편의를 위해 전역 함수 덮어쓰기 (Monkey Patching 느낌으로 사용)
        search_similar_questions = local_search_similar_questions

        if choice == '1':
            run_interactive_mode(model, conn)
        elif choice == '2':
            run_batch_mode(model, conn)
        else:
            print("잘못된 선택입니다.")
            
    finally:
        conn.close()
        print("\nDB 연결 종료.")