# -*- coding: utf-8 -*-
"""
DB 리셋(초기화) 스크립트

[경고] 이 스크립트를 실행하면 4개의 마스터 테이블과
모든 데이터(ETL, 임베딩 벡터)가 영구적으로 삭제됩니다!

모든 ETL/임베딩 스크립트를 재실행하기 전에 DB를 깨끗하게 비울 때 사용하세요.
"""

import traceback
import psycopg2 
from dotenv import load_dotenv,find_dotenv 
import os

# --- 1. .env 파일 로드 ---
# .env 파일에서 환경 변수를 로드합니다.

load_dotenv(find_dotenv())

# --- 2. 설정 (Configuration) ---
# .env 파일에서 DB 접속 정보를 읽어옵니다.
DB_HOST = os.getenv('DB_HOST','localhost') 
DB_PORT = os.getenv('DB_PORT','5432')
DB_NAME = os.getenv('DB_NAME') 
DB_USER = os.getenv('DB_USER','postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

print("DB_HOST =", os.getenv("DB_HOST"))
print("DB_PORT =", os.getenv("DB_PORT"))
print("DB_NAME =", os.getenv("DB_NAME"))
print("DB_USER =", os.getenv("DB_USER"))
print("DB_PASSWORD =", os.getenv("DB_PASSWORD"))
print("INPUT_PATH =", os.getenv("INPUT_PATH"))

# [방어 코드] 스크립트 실행에 필수적인 값들이 .env에 없는지 확인합니다.
if not all([DB_NAME, DB_PASSWORD]):
    print("XXX [오류] .env 파일에 DB_NAME 또는 DB_PASSWORD가 설정되지 않았습니다.")
    exit()

# 삭제할 테이블 이름 정의
RESPONDENTS_TABLE = 'respondents' 
METADATA_TABLE = 'metadata' 
CODEBOOKS_TABLE = 'codebooks' 
ANSWERS_TABLE = 'answers' 

# --- 3. 메인 실행 함수 ---
def drop_all_tables():
    """DB에 연결하여 4개의 마스터 테이블을 모두 DROP합니다."""
    
    conn = None # conn 변수 초기화
    try:
        # DB 연결
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True # DROP TABLE은 트랜잭션 외부에서 실행하는 것이 안전할 수 있음
        print(">>> [Phase 1] PostgreSQL DB 연결 성공.")

        with conn.cursor() as cur:
            print(">>> [Phase 2] 4개 마스터 테이블 삭제(DROP) 시도...")

            # 1. respondents 테이블을 'CASCADE'로 삭제
            #    (answers와 metadata가 이 테이블을 참조하므로, CASCADE로 동시 삭제)
            print(f"  [Info] DROP TABLE {RESPONDENTS_TABLE} CASCADE...")
            cur.execute(f"DROP TABLE IF EXISTS {RESPONDENTS_TABLE} CASCADE;")

            # 2. codebooks 테이블 삭제 (독립 테이블)
            print(f"  [Info] DROP TABLE {CODEBOOKS_TABLE} CASCADE...")
            cur.execute(f"DROP TABLE IF EXISTS {CODEBOOKS_TABLE} CASCADE;")
            
            # 3. (확인 사살)
            #    혹시 FK 관계가 깨져있을 경우를 대비해 answers, metadata도 명시적으로 삭제
            print(f"  [Info] DROP TABLE {ANSWERS_TABLE} CASCADE (확인)...")
            cur.execute(f"DROP TABLE IF EXISTS {ANSWERS_TABLE} CASCADE;")
            print(f"  [Info] DROP TABLE {METADATA_TABLE} CASCADE (확인)...")
            cur.execute(f"DROP TABLE IF EXISTS {METADATA_TABLE} CASCADE;")

            print("\n>>> [Success] 4개의 마스터 테이블(respondents, metadata, codebooks, answers)이 모두 삭제되었습니다.")

    except psycopg2.Error as e:
        # DB 연결 또는 DROP 실행 중 오류 발생
        print(f"\nXXX [오류] 테이블 삭제 중 오류 발생: {e}")
        traceback.print_exc()
    
    finally:
        # 5. 스크립트가 성공하든, 오류로 중단되든 항상 DB 연결을 닫습니다.
        if conn:
            conn.close()
            print(">>> [Phase 3] PostgreSQL DB 연결 종료.")

# --- 4. 스크립트 실행 ---
if __name__ == "__main__":
    # 이 스크립트는 위험하므로, 실행 전 사용자 확인을 받는 것이 좋습니다.
    print("[경고] 이 스크립트는 DB의 4개 마스터 테이블을 영구적으로 삭제합니다!")
    confirm = input("정말로 실행하시겠습니까? (y/n): ")
    
    if confirm.lower() == 'y':
        drop_all_tables()
    else:
        print("작업이 취소되었습니다.")
