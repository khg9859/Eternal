# -*- coding: utf-8 -*-
"""
Welcome 2nd ETL 스크립트 (Append-Only, INT Age, NaN/ETC Fix Version)

[스크립트의 목적]
이 스크립트는 'Welcome_2nd' 데이터 (데이터 CSV, 코드북 CSV)를 읽어와서
PostgreSQL 데이터베이스의 'respondents', 'codebooks', 'answers' 테이블에 삽입합니다.

[중요] 이 스크립트는 'metadata' 테이블을 채우지 않습니다.
(metadata는 'welcome_1st'와 'qpoll' 스크립트가 담당)

[주요 기능]
1. .env 파일을 통해 DB 접속 정보를 안전하게 로드합니다.
2. 4개 마스터 테이블이 ('birth_year INT', 'age INT' 스키마로) 없으면 생성합니다. (IF NOT EXISTS)
3. 'welcome_2nd_codebook.csv' (수직 형식) 파일을 파싱하여 'codebooks' 테이블에 삽입합니다.
   - [수정] 'Q'로 시작하는 'var_name'만 새 질문으로 인식하고,
     'Q'로 시작하지 않는 'var_name'은 '보기(qi_val)'로 인식하여 'w2_1004' 같은 잉여 데이터 문제를 해결합니다.
4. 'welcome_2nd.csv' (데이터 파일)을 파싱하여 'respondents', 'answers' 테이블에 삽입합니다.
   - [수정] pd.isna() 및 'nan' 문자열 검사를 통해 빈 ID가 DB에 삽입되는 오류를 수정합니다.
5. 'w2_' 접두사(prefix)를 사용하여 다른 데이터 소스(qpoll 등)와 ID가 충돌하지 않도록 합니다.
"""

# --- 1. 라이브러리 임포트 ---
import psycopg2 # PostgreSQL DB 어댑터
from psycopg2.extras import execute_values # 대량 INSERT를 위한 psycopg2 헬퍼
import pandas as pd # 데이터 분석 및 CSV 파일 읽기용 라이브러리
import json # 코드북 데이터를 JSON 문자열로 변환하기 위함
import os # .env 값(환경 변수)을 읽고, 파일 경로를 다루기 위함
from dotenv import load_dotenv,find_dotenv  # .env 파일에서 환경 변수를 로드하기 위함

# --- 2. .env 파일 로드 ---
# [필수] 스크립트 시작 시 .env 파일에 정의된 변수들을 '환경 변수'로 로드합니다.
load_dotenv(find_dotenv())

# --- 3. 설정 (Configuration) ---
# .env 파일에서 DB 접속 정보를 읽어옵니다.
DB_HOST = os.getenv('DB_HOST','localhost') 
DB_PORT = os.getenv('DB_PORT','5432')
DB_NAME = os.getenv('DB_NAME') 
DB_USER = os.getenv('DB_USER','postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# .env 파일에서 데이터 파일 경로를 읽어옵니다.
INPUT_FOLDER = os.getenv('INPUT_PATH')

# [방어 코드] 스크립트 실행에 필수적인 값들이 .env에 없는지 확인합니다.
if not all([DB_NAME, DB_PASSWORD, INPUT_FOLDER]):
    print("XXX [오류] .env 파일에 DB_NAME, DB_PASSWORD, INPUT_PATH 중 하나 이상이 설정되지 않았습니다.")
    exit() # 스크립트 강제 종료

# 이 스크립트가 처리할 Welcome 2nd 파일의 정확한 이름
DATA_FILE = 'wel_2nd_test.csv'
CODEBOOK_FILE = 'welcome_2nd_codebook.csv'
# 'w2_' 접두사: qpoll('qp...'), welcome_1st(메타데이터만)와 데이터가 섞이지 않도록 함
PREFIX = 'w2_' 

# 마스터 테이블 이름 정의
RESPONDENTS_TABLE = 'respondents'
ANSWERS_TABLE = 'answers'
CODEBOOKS_TABLE = 'codebooks'
# (metadata 테이블 이름은 알지만, 이 스크립트에서는 사용하지 않음)
METADATA_TABLE = 'metadata' 

# --- 4. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
    print(">>> [Phase 1] PostgreSQL DB 연결 시도...")
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

# --- 5. 마스터 테이블 확인/생성 함수 ---
def setup_master_tables(conn):
    """
    [Append-Only] [수정] 'birth_year INT', 'age INT' 스키마로 4개 테이블이 없으면 생성합니다.
    (기존 데이터 보존을 위해 DROP하지 않습니다.)
    """
    # 4개 테이블의 'CREATE TABLE IF NOT EXISTS' 쿼리 목록
    queries = [
        # 1. respondents (qpoll과 동일한 구조)
        f"CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (mb_sn VARCHAR(255) PRIMARY KEY, profile_vector TEXT DEFAULT NULL);",
        
        # 2. metadata [수정] (qpoll/welcome_1st과 동일한 'birth_year INT', 'age INT' 스키마)
        f"""CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            metadata_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            mobile_carrier VARCHAR(100) DEFAULT NULL,
            gender VARCHAR(10) DEFAULT NULL,
            birth_year INT DEFAULT NULL, 
            age INT DEFAULT NULL, 
            region VARCHAR(100) DEFAULT NULL
        );""",

        # 3. codebooks (qpoll과 동일한 구조)
        f"CREATE TABLE IF NOT EXISTS {CODEBOOKS_TABLE} (codebook_id VARCHAR(255) PRIMARY KEY, codebook_data JSONB);",
        
        # 4. answers (qpoll과 동일한 구조)
        f"""CREATE TABLE IF NOT EXISTS {ANSWERS_TABLE} (
            answer_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            question_id VARCHAR(255), 
            answer_value TEXT
        );"""
    ]
    
    cur = conn.cursor()
    try:
        print(">>> [Phase 2] 마스터 테이블 (respondents, metadata, codebooks, answers) 셋업 확인...")
        for query in queries:
            cur.execute(query)
        conn.commit() 
        return True
    except Exception as e:
        print(f"XXX [Phase 2] 테이블 설정 중 오류 발생: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

# --- 6. [신규] 헬퍼 함수 (데이터 정제용) ---
def clean_cell(val):
    """
    [qpoll 스크립트와 동일]
    pandas/numpy의 NaN 및 'nan' 문자열을 안전하게 처리하여
    DB에 'nan' 텍스트가 삽입되는 것을 방지합니다.
    """
    if pd.isna(val):
        return '' # NaN이면 빈 문자열 반환
    s = str(val).strip()
    if s.lower() == 'nan':
        return '' # 'nan' 문자열도 빈 문자열로 반환
    return s

# --- 7. Welcome 2nd 코드북 ETL 함수 (Pass 1) ---
def process_codebook_etl(conn, file_path, prefix):
    """[수정] 'welcome_2nd_codebook.csv' (수직 형식) 코드북을 파싱하여 DB에 삽입합니다."""
    print(f"  [Stage 1] '{file_path}'의 Welcome 2nd 코드북 처리 시작 (Prefix: {prefix})...")

    try:
        try:
            df_codebook = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df_codebook = pd.read_csv(file_path, encoding='cp949')

        # [수정] 딕셔너리를 사용하여 중복 ID 덮어쓰기
        codebook_dict = {}
        
        current_question_id = None 
        current_question_title = None 
        current_answers = [] 

        for row in df_codebook.itertuples(index=False):
            # [수정] clean_cell을 적용하여 'nan' 문자열 방지
            var_name = clean_cell(row[0])      # 1열 (변수명)
            question_text = clean_cell(row[1]) # 2열 (문항)
            # question_type = clean_cell(row[2]) # 3열 (문항유형) - 이 로직에서는 사용 안 함

            # [수정] 잉여 데이터('w2_1004') 버그 수정
            # 1열(var_name)이 'Q'로 시작하면 "새로운 질문"으로 간주합니다.
            if var_name and var_name.strip().startswith('Q'):
                
                # 이전에 처리 중이던 질문(current_question_id)이 있었다면,
                # 딕셔너리에 저장합니다.
                if current_question_id:
                    unique_id = f"{prefix}{current_question_id}"
                    codebook_dict[unique_id] = {
                        "codebook_id": unique_id,
                        "q_title": current_question_title,
                        "answers": current_answers
                    }

                # 새로 발견된 질문 정보로 변수 업데이트
                current_question_id = var_name
                current_question_title = question_text
                current_answers = [] # 보기 목록 초기화

            # [수정] "보기 항목" 처리
            # 1열(var_name)이 'Q'로 시작하지 *않고*, 1열과 2열에 모두 값이 있다면
            # (예: '1', '미혼' 또는 '590', '리베로' 또는 'w2_1004', 'GV80')
            # 이는 'current_question_id'에 속한 "보기"로 간주합니다.
            elif var_name and question_text:
                if current_question_id: # (현재 속한 질문이 있을 경우에만)
                    qi_val = var_name      # 1열 값 (예: '1' 또는 '590')
                    qi_title = question_text # 2열 값 (예: '미혼' 또는 '리베로')
                    current_answers.append({"qi_val": qi_val, "qi_title": qi_title})
            
            # (1열이 비어있거나, 1열은 있는데 2열이 비어있으면 무시)

        # 마지막 질문 저장 (루프가 끝난 후, 미처 저장되지 못한 마지막 질문을 저장)
        if current_question_id:
            unique_id = f"{prefix}{current_question_id}"
            codebook_dict[unique_id] = {
                "codebook_id": unique_id,
                "q_title": current_question_title,
                "answers": current_answers
            }
        
        print(f"  [Stage 1] 코드북 파싱 완료. {len(codebook_dict)}개의 질문 항목 감지.")

        # --- DB에 삽입 ---
        data_to_insert = []
        # [수정] 딕셔너리에서 (ID, JSON) 튜플 리스트 생성
        for unique_id, codebook_obj in codebook_dict.items():
            # 'mb_sn'은 질문이 아니므로 코드북에 삽입하지 않음
            if unique_id == f"{prefix}mb_sn":
                continue
            json_data_string = json.dumps(codebook_obj, ensure_ascii=False)
            data_to_insert.append((unique_id, json_data_string))

        if data_to_insert:
            cur = conn.cursor()
            try:
                # INSERT ... ON CONFLICT ...
                insert_query = f"""
                INSERT INTO {CODEBOOKS_TABLE} (codebook_id, codebook_data)
                VALUES %s
                ON CONFLICT (codebook_id) DO UPDATE SET
                    codebook_data = EXCLUDED.codebook_data;
                """
                execute_values(cur, insert_query, data_to_insert)
                conn.commit()
                print(f"  [Stage 1] 코드북 데이터 {len(data_to_insert)}건 저장 완료.")
            except Exception as e:
                print(f"  XXX [Stage 1] 코드북 DB 삽입 중 오류 발생: {e}")
                conn.rollback()
            finally:
                cur.close()

        return True

    except Exception as e:
        print(f"  XXX [Stage 1] 코드북 파일 처리 중 오류 발생: {e}")
        return False


# --- 8. Welcome 2nd 데이터 ETL 함수 (Pass 2) ---
def process_data_etl(conn, file_path, prefix):
    """[수정] 'nan' 버그를 수정한 'welcome_2nd.csv' 파싱 함수"""
    print(f"  [Stage 2] '{file_path}'의 Welcome 2nd 데이터 처리 시작 (Prefix: {prefix})...")
    
    respondents_to_insert = set() 
    answers_to_insert = []
    
    try:
        try:
            df_panel = pd.read_csv(file_path, encoding='utf-8',dtype=str)
        except UnicodeDecodeError:
            df_panel = pd.read_csv(file_path, encoding='cp949',dtype=str)

        mb_sn_col_name = 'mb_sn' 
        if mb_sn_col_name not in df_panel.columns:
            print(f"  XXX [Stage 2] 오류: '{mb_sn_col_name}' ID 컬럼이 없습니다. 건너뜁니다.")
            return False

        print("  [Stage 2] 데이터 변환(Unpivot, 콤마 분리) 시작...")
        
        dropped_rows_count = 0 # [신규] NaN ID로 인해 건너뛴 행 카운트
        
        for row in df_panel.itertuples(index=False):
            row_dict = row._asdict()
            
            # [수정] 'nan' 문자열 삽입 버그 수정
            raw_mb_sn = row_dict.get(mb_sn_col_name)
            mb_sn = clean_cell(raw_mb_sn) # NaN, 'nan' -> ''
            
            if not mb_sn: 
                dropped_rows_count += 1
                continue # ID 없는 행 무시
            
            # (1) respondents 테이블 데이터 추출
            respondents_to_insert.add((mb_sn,)) 

            # (2) metadata 테이블 처리는 이 스크립트에서 생략

            # (3) answers 테이블 데이터 추출 (Unpivot 과정)
            for question_id, raw_answer_value in row_dict.items():
                
                # ID 컬럼이거나, 값이 비어있으면(NaN) 건너뜀
                if (question_id == mb_sn_col_name): 
                    continue
                
                # [수정] clean_cell을 사용하여 pd.isna()와 'nan' 문자열을 한 번에 처리
                answer_string = clean_cell(raw_answer_value)
                if not answer_string: # (NaN, 'nan', '' 모두 포함)
                    continue

                unique_question_id = f"{prefix}{question_id}"

                # 콤마(,)로 구분된 다중 응답 처리 (e.g., "1, 3, 4")
                split_values = [val.strip() for val in answer_string.split(',') if val.strip()]

                for final_value in split_values:
                    answers_to_insert.append((mb_sn, unique_question_id, final_value))

        print(f"  [Stage 2] 데이터 변환 완료. (ID 없는 {dropped_rows_count}개 행 건너뜀)")
        print(f"  [Stage 2] {len(respondents_to_insert)}명, {len(answers_to_insert)}개 답변 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # (1) Respondents 삽입
            if respondents_to_insert:
                respondents_query = f"""
                INSERT INTO {RESPONDENTS_TABLE} (mb_sn) 
                VALUES %s 
                ON CONFLICT (mb_sn) DO NOTHING; 
                """
                execute_values(cur, respondents_query, list(respondents_to_insert))
            
            # (2) Metadata 삽입 (생략)

            # (3) Answers 삽입 (멱등성 보장)
            respondent_ids_in_this_file = list(respondents_to_insert) 
            if respondent_ids_in_this_file:
                respondent_id_list = [r[0] for r in respondent_ids_in_this_file]
                
                print(f"  [Stage 2] '{ANSWERS_TABLE}' 테이블에서 기존 'w2_' 답변 삭제 중...")
                cur.execute(
                    f"DELETE FROM {ANSWERS_TABLE} WHERE mb_sn = ANY(%s) AND question_id LIKE %s;",
                    (respondent_id_list, f"{prefix}%") 
                )

            # Answers 대량 삽입
            if answers_to_insert:
                print(f"  [Stage 2] '{ANSWERS_TABLE}' 테이블에 {len(answers_to_insert)}건 삽입 중...")
                answers_query = f"""
                INSERT INTO {ANSWERS_TABLE} (mb_sn, question_id, answer_value) 
                VALUES %s;
                """
                execute_values(cur, answers_query, answers_to_insert)

            conn.commit() 
            print(f"  [Stage 2] 패널 데이터가 마스터 DB에 성공적으로 저장되었습니다.")
            return True
            
        except Exception as e:
            print(f"  XXX [Stage 2] 패널 데이터 DB 삽입 중 오류 발생: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()

    except Exception as e:
        print(f"  XXX [Stage 2] 패널 데이터 파일 처리 중 오류 발생: {e}")
        return False


# --- 9. 메인 실행 파이프라인 ---
def main():
    db_conn = connect_to_db() # 1. DB 연결
    if db_conn:
        try:
            # 2. 4개 마스터 테이블이 없으면 생성
            if not setup_master_tables(db_conn):
                print("오류: 마스터 테이블 셋업에 실패하여 ETL을 중단합니다.")
                db_conn.close()
                return
            
            print(f">>> [Phase 3] Welcome 2nd 파일 처리 시작...")
            
            # 3. .env에서 읽어온 INPUT_FOLDER와 파일 이름을 조합하여 전체 경로 생성
            codebook_path = os.path.join(INPUT_FOLDER, CODEBOOK_FILE)
            data_path = os.path.join(INPUT_FOLDER, DATA_FILE)
            
            # 4. 파일 존재 여부 확인
            if not os.path.exists(codebook_path):
                print(f"XXX 오류: 코드북 파일을 찾을 수 없습니다: {codebook_path}")
                return
            if not os.path.exists(data_path):
                print(f"XXX 오류: 데이터 파일을 찾을 수 없습니다: {data_path}")
                return

            # Pass 1: 코드북 삽입
            print("\n--- ETL Pass 1: Welcome 2nd 코드북 처리 ---")
            process_codebook_etl(db_conn, codebook_path, PREFIX)

            # Pass 2: 패널 데이터 삽입
            print("\n--- ETL Pass 2: Welcome 2nd 패널 데이터 처리 ---")
            process_data_etl(db_conn, data_path, PREFIX)

            print("\n>>> [Phase 4] Welcome 2nd ETL 작업이 완료되었습니다.")

        except Exception as e:
            print(f"XXX 메인 실행 중 오류 발생: {e}")
            db_conn.rollback()
        finally:
            # 5. 스크립트가 성공하든 실패하든 DB 연결 종료
            db_conn.close()
            print(">>> [Phase 5] PostgreSQL DB 연결 종료.")

# --- 10. 스크립트 실행 ---
if __name__ == '__main__':
    main()