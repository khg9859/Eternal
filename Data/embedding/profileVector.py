# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# CREATE PROFILE VECTORS (Phase 5 Only)
# -----------------------------------------------------------------
# 이 스크립트는 'answers' 테이블에 이미 존재하는 'a_vector'들을
# 읽어와, 'respondents' 테이블의 'profile_vector'를
# (재)생성하는 작업(Phase 5)만 수행합니다.
#
# [요구 라이브러리]
# pip install psycopg2-binary numpy
# -----------------------------------------------------------------

import psycopg2
from psycopg2.extras import execute_values
import numpy as np
import os
import time
import json  # JSON 파싱을 위해 임포트

# --- 설정 (Configuration) ---
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'capstone'
DB_USER = 'postgres'
DB_PASSWORD = 'Sjw@040107'

# [중요!] 'a_vector'의 실제 차원과 동일해야 합니다!
EMBEDDING_DIMENSION = 1024
# DB에 한 번에 업데이트할 배치 크기
BATCH_SIZE = 500
# [수정] Server-Side Cursor가 한 번에 가져올 청크(Chunk) 크기
CURSOR_FETCH_CHUNK = 2000

# --- 테이블 이름 (ETL 스크립트와 동일해야 함) ---
RESPONDENTS_TABLE = 'respondents'
ANSWERS_TABLE = 'answers'

# --- 1. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        print(">>> [Phase 1] PostgreSQL DB 연결 성공.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"XXX [Phase 1] DB 연결 실패: {e}")
        return None

# --- 헬퍼 함수: 벡터 컬럼 초기화 ---
def setup_profile_vector_column(conn):
    """profile_vector 컬럼을 재생성합니다. (Server-Side Cursor 충돌 방지를 위해 분리)"""
    # 이 함수는 DDL을 실행하므로 별도 트랜잭션으로 관리합니다.
    with conn.cursor() as cur:
        try:
            print("   [Info] 'respondents' 테이블의 'profile_vector' 컬럼 확인/재생성 중...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"ALTER TABLE {RESPONDENTS_TABLE} DROP COLUMN IF EXISTS profile_vector;")
            cur.execute(f"ALTER TABLE {RESPONDENTS_TABLE} ADD COLUMN profile_vector VECTOR({EMBEDDING_DIMENSION});")
            conn.commit()
            print("   [Info] 'profile_vector' 컬럼 준비 완료.")
            return True
        except Exception as e:
            print(f"XXX 컬럼 초기화 중 오류: {e}")
            conn.rollback()
            return False


# --- [수정] 헬퍼 함수: 평균 벡터 계산 ---
# 이제 이 함수는 문자열이 아닌, 파싱된 숫자 리스트를 받습니다.
def calculate_mean_vector(vector_list):
    """NumPy를 사용해 벡터 리스트의 평균을 계산하고 0벡터를 필터링합니다."""
    if not vector_list:
        return None

    try:
        # vector_list는 이제 [ [0.1, 0.2, ...], [0.4, 0.5, ...] ] 형태의 숫자 리스트입니다.
        profile_matrix = np.array(vector_list, dtype=np.float32)

        # 0벡터 필터링
        norms = np.linalg.norm(profile_matrix, axis=1)
        nonzero_vectors = profile_matrix[norms > 0.0]
        
        if nonzero_vectors.shape[0] == 0:
            return None  # 0벡터만 있었던 경우
        
        # 0벡터가 아닌 벡터들로만 평균을 계산
        mean_vector = np.mean(nonzero_vectors, axis=0)
        return mean_vector.tolist()

    except Exception as e:
        # NumPy에서 float 변환 실패 시 (데이터가 여전히 문자열인 경우)
        print(f"   [Warning] NumPy 평균 계산 중 오류 (무시): {e}")
        return None

# --- 2. [수정됨] 통합 프로필 벡터 생성 함수 (OOM 방지) ---
def create_respondent_profiles(conn_read, conn_write):
    """
    [OOM 방지] SQL의 array_agg 대신 Python에서 스트리밍으로
    벡터 평균을 계산하여 profile_vector를 생성합니다.
    **읽기용(conn_read)과 쓰기용(conn_write) 연결을 분리해야 합니다.**
    """
    print("\n>>> [Phase 5] 통합 프로필 벡터(Respondents) 생성 시작...")
    
    # Server-Side Cursor 생성 (읽기 전용 연결 사용)
    # 'name' 인자를 지정하여 서버 사이드 커서를 명시적으로 사용합니다.
    cur = conn_read.cursor('profile_cursor') 
    
    # 업데이트용 커서 (쓰기 전용 연결 사용)
    update_cur = conn_write.cursor() 

    try:
        print("   [Info] 사용자별 답변 벡터(a_vector) 스트리밍 집계 시작...")
        
        query = f"""
            SELECT mb_sn, a_vector
            FROM {ANSWERS_TABLE}
            WHERE a_vector IS NOT NULL
            ORDER BY mb_sn;
        """ 
        
        cur.execute(query) 
        
        total_profiles_processed = 0
        update_data = [] # (profile_vector, mb_sn)
        
        current_mb_sn = None
        current_vectors = []

        # fetchmany를 사용해 정렬된 데이터를 청크(chunk) 단위로 스트리밍
        while True:
            rows = cur.fetchmany(CURSOR_FETCH_CHUNK)
            if not rows:
                break # 루프 종료

            for row in rows:
                mb_sn, a_vector_data = row # a_vector는 문자열('[0.1, ...]')일 수 있습니다.
                
                a_vector = None
                if a_vector_data:
                    try:
                        # [!!!] 수정된 부분: 이중 인코딩을 처리하기 위한 파싱 로직
                        parsed_data = json.loads(a_vector_data)
                        
                        # 만약 파싱 결과가 여전히 문자열이면 (이중 인코딩된 경우)
                        if isinstance(parsed_data, str):
                            a_vector = json.loads(parsed_data) # 다시 파싱
                        else:
                            a_vector = parsed_data
                        
                        # 파싱된 데이터가 리스트인지 최종 확인
                        if not isinstance(a_vector, list):
                            raise TypeError("Parsed data is not a list")
                            
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"  [Warning] mb_sn {mb_sn}의 벡터 파싱 실패. 해당 답변을 건너뜁니다. 데이터: '{str(a_vector_data)[:50]}...', 오류: {e}")
                        continue # 이 답변 벡터는 건너뜀
                
                if a_vector is None:
                    continue # Null이거나 파싱 실패한 벡터는 무시

                # [핵심] mb_sn이 바뀌는 시점 (새로운 사용자의 시작)
                if current_mb_sn is not None and mb_sn != current_mb_sn:
                    # 1. "이전" 사용자의 평균 벡터를 계산합니다.
                    mean_vector = calculate_mean_vector(current_vectors)
                    
                    if mean_vector:
                        update_data.append((mean_vector, current_mb_sn))
                    
                    # 2. 다음 사용자를 위해 리스트를 리셋합니다.
                    current_mb_sn = mb_sn
                    current_vectors = [a_vector]
                else:
                    # "현재" 사용자의 벡터를 리스트에 계속 추가합니다.
                    if current_mb_sn is None: # 첫 번째 사용자인 경우
                        current_mb_sn = mb_sn
                    current_vectors.append(a_vector)

                # --- DB에 일괄 업데이트 (배치 처리) ---
                if len(update_data) >= BATCH_SIZE:
                    print(f"   [Info] {len(update_data)}명의 프로필 벡터를 DB에 저장합니다 (현재 사용자: {current_mb_sn})...")
                    update_query = f"""
                        UPDATE {RESPONDENTS_TABLE} SET profile_vector = data.profile_vector
                        FROM (VALUES %s) AS data (profile_vector, mb_sn)
                        WHERE {RESPONDENTS_TABLE}.mb_sn = data.mb_sn;
                    """
                    execute_values(update_cur, update_query, update_data, page_size=BATCH_SIZE)
                    conn_write.commit() # [!!!] 쓰기 전용 연결(conn_write)을 커밋합니다.
                    total_profiles_processed += len(update_data)
                    update_data = [] # 리스트 비우기

        # --- 루프 종료 후, "마지막" 사용자의 데이터를 처리 ---
        if current_mb_sn is not None and current_vectors:
            mean_vector = calculate_mean_vector(current_vectors)
            if mean_vector:
                update_data.append((mean_vector, current_mb_sn))

        # --- 최종 잔여 데이터 업데이트 ---
        if update_data:
            print(f"   [Info] 잔여 {len(update_data)}명의 프로필 벡터를 DB에 저장합니다...")
            update_query = f"""
                UPDATE {RESPONDENTS_TABLE} SET profile_vector = data.profile_vector
                FROM (VALUES %s) AS data (profile_vector, mb_sn)
                WHERE {RESPONDENTS_TABLE}.mb_sn = data.mb_sn;
            """
            execute_values(update_cur, update_query, update_data, page_size=BATCH_SIZE)
            conn_write.commit() # [!!!] 쓰기 전용 연결(conn_write)을 커밋합니다.
            total_profiles_processed += len(update_data)
            
        print(f"   [Success] 총 {total_profiles_processed}명의 통합 프로필 벡터 저장 완료.")

    except Exception as e:
        print(f"   XXX [Phase 5] 프로필 벡터 생성 중 치명적 오류 발생: {e}")
        conn_write.rollback() # [!!!] 쓰기 전용 연결(conn_write)을 롤백합니다.
    finally:
        # [중요] 커서가 이미 닫혔거나 무효화되어도 오류가 나지 않도록
        # 개별적으로 try-except 처리합니다.
        try:
            cur.close()
        except Exception as e:
            print(f"   [Info] 읽기 커서 닫기 중 무시된 오류: {e}")
            
        try:
            update_cur.close()
        except Exception as e:
            print(f"   [Info] 쓰기 커서 닫기 중 무시된 오류: {e}")


# --- 3. 메인 실행 파이프라인 ---
def main():
    print("===== 통합 프로필 벡터 생성 (Phase 5) 스크립트 시작 =====")
    
    start_time = time.time()
    
    # [!!!] 읽기용, 쓰기용으로 두 개의 커넥션을 생성합니다.
    conn_read = None
    conn_write = None
    
    try:
        conn_read = connect_to_db() 
        conn_write = connect_to_db()
        
        if not conn_read or not conn_write:
            print("XXX DB 연결에 실패하여 스크립트를 종료합니다.")
            return

        # 1. profile_vector 컬럼 초기화 (하나의 연결로 DDL 수행)
        if not setup_profile_vector_column(conn_write):
            return
        
        print(">>> [Phase 2, 3, 4] 건너뛰기 - a_vector 및 q_vector가 이미 생성된 것으로 간주합니다.")

        # 2. Respondent (통합 프로필) 생성 실행 (두 개의 연결 전달)
        create_respondent_profiles(conn_read, conn_write)

        end_time = time.time()
        print(f"\n>>> [Success] 통합 프로필 벡터 생성이 완료되었습니다. (총 소요 시간: {end_time - start_time:.2f}초)")

    except Exception as e:
        print(f"XXX 메인 실행 중 치명적 오류 발생: {e}")
        # 롤백은 쓰기 연결에만 필요할 수 있습니다.
        if conn_write:
            conn_write.rollback()
    finally:
        # [!!!] 두 연결을 모두 닫습니다.
        if conn_read:
            conn_read.close()
            print(">>> [Phase 6] PostgreSQL (Read) DB 연결 종료.")
        if conn_write:
            conn_write.close()
            print(">>> [Phase 6] PostgreSQL (Write) DB 연결 종료.")

# --- 스크립트 실행 ---
if __name__ == '__main__':
    main()

