# -*- coding: utf-8 -*-
"""
Welcome 2nd ETL 스크립트 (Append-Only 버전)

이 스크립트는 'Welcome_2nd' 데이터 (데이터 CSV, 코드북 CSV)를 읽어와서
PostgreSQL 데이터베이스의 'respondents', 'codebooks', 'answers' 테이블에 삽입합니다.

[중요] 이 스크립트는 'metadata' 테이블을 채우지 않습니다.
(metadata는 'welcome_1st'와 'qpoll' 스크립트가 담당)

주요 기능:
1. .env 파일을 통해 DB 접속 정보를 안전하게 로드합니다.
2. 4개의 마스터 테이블이 없으면 생성합니다. (IF NOT EXISTS)
- [중요] 기존 데이터를 보존하기 위해 테이블을 삭제(DROP)하지 않습니다.
3. 'welcome_2nd_codebook.csv' (수직 형식) 파일을 파싱하여 'codebooks' 테이블에 삽입합니다.
4. 'wel_2ndex.csv' (데이터 파일)을 파싱하여 'respondents', 'answers' 테이블에 삽입합니다.
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
DATA_FILE = 'wel_2ndex.csv'
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
    [Append-Only] 4개의 마스터 테이블이 없으면 생성합니다.
    (기존 데이터 보존을 위해 DROP하지 않습니다.)
    """
    # 4개 테이블의 'CREATE TABLE IF NOT EXISTS' 쿼리 목록
    # 이 쿼리들은 테이블이 이미 존재하면 무시됩니다.
    queries = [
        # 1. respondents (welcome_1st와 동일한 구조)
        f"CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (mb_sn VARCHAR(255) PRIMARY KEY, profile_vector TEXT DEFAULT NULL);",
        # 2. metadata (welcome_1st와 동일한 구조, 이 스크립트는 여기 삽입 안 함)
        f"""CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            metadata_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            mobile_carrier VARCHAR(100) DEFAULT NULL,
            gender VARCHAR(10) DEFAULT NULL,
            age VARCHAR(50) DEFAULT NULL, 
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
        # 4개의 쿼리를 순차적으로 실행
        for query in queries:
            cur.execute(query)
        conn.commit() # 4개 테이블 생성을 DB에 최종 반영
        return True
    except Exception as e:
        print(f"XXX [Phase 2] 테이블 설정 중 오류 발생: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

# --- 6. Welcome 2nd 코드북 ETL 함수 (Pass 1) ---
def process_codebook_etl(conn, file_path, prefix):
    """'welcome_2nd_codebook.csv' (수직 형식) 코드북을 파싱하여 DB에 삽입합니다."""
    print(f"  [Stage 1] '{file_path}'의 Welcome 2nd 코드북 처리 시작 (Prefix: {prefix})...")

    try:
        # CSV 읽기 (UTF-8 시도 -> 실패 시 CP949)
        try:
            df_codebook = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df_codebook = pd.read_csv(file_path, encoding='cp949')

        # '수직' 형식 코드북을 파싱하기 위한 변수
        codebook_objects = [] # 파싱된 JSON 객체들을 임시 저장할 리스트
        current_question_id = None # 현재 처리 중인 질문 ID (예: 'Q1')
        current_question_title = None # 현재 처리 중인 질문 제목 (예: '결혼여부')
        current_answers = [] # 현재 질문의 보기 목록 (예: [{"qi_val": "1", "qi_title": "미혼"}])

        # CSV를 한 줄씩 순회
        for row in df_codebook.itertuples(index=False):
            var_name = str(row[0]).strip() # 1열 (변수명)
            question_text = str(row[1]).strip() # 2열 (문항)
            question_type = str(row[2]).strip() # 3열 (문항유형)

            # 1열(var_name)에 값이 있으면 '새로운 질문'의 시작으로 간주
            # (pandas가 빈 셀을 'nan'으로 읽을 수 있으므로 pd.notna 확인)
            if pd.notna(row[0]) and var_name:
                
                # [중요] 이전에 처리 중이던 질문(current_question_id)이 있었다면,
                # 'codebook_objects' 리스트에 저장하고 변수를 초기화합니다.
                if current_question_id:
                    obj = {
                        "codebook_id": f"{prefix}{current_question_id}", # 예: "w2_Q1"
                        "q_title": current_question_title,
                        "answers": current_answers
                    }
                    codebook_objects.append(obj)

                # 새로 발견된 질문 정보로 변수 업데이트
                current_question_id = var_name
                current_question_title = question_text
                current_answers = [] # 보기 목록 초기화

            # '보기 항목' 처리 (1열이 비어있고, 2열과 3열에 값이 있는 경우)
            elif pd.notna(row[1]) and pd.notna(row[2]):
                qi_val = question_text  # 2열 값 (예: '1')
                qi_title = question_type # 3열 값 (예: '미혼')

                # [중요] 2열이 숫자이고, 3열이 'SINGLE', 'Numeric' 같은 타입 설명이 아닌 경우
                # (즉, '1', '미혼' 처럼 실제 "보기" 항목인 경우)
                if qi_val.isdigit() and qi_title not in ('SINGLE', 'Numeric', 'String', 'nan'):
                    current_answers.append({"qi_val": qi_val, "qi_title": qi_title})

        # 마지막 질문 저장 (루프가 끝난 후, 미처 저장되지 못한 마지막 질문을 저장)
        if current_question_id:
            obj = {
                "codebook_id": f"{prefix}{current_question_id}",
                "q_title": current_question_title,
                "answers": current_answers
            }
            codebook_objects.append(obj)

        print(f"  [Stage 1] 코드북 파싱 완료. {len(codebook_objects)}개의 질문 항목 감지.")

        # --- DB에 삽입 ---
        data_to_insert = []
        for codebook_obj in codebook_objects:
            # 'mb_sn'은 질문이 아니므로 코드북에 삽입하지 않음
            if codebook_obj["codebook_id"] == f"{prefix}mb_sn":
                continue
            unique_id = codebook_obj["codebook_id"]
            # JSON 객체를 한글(utf-8)이 깨지지 않는 문자열로 변환
            json_data_string = json.dumps(codebook_obj, ensure_ascii=False)
            data_to_insert.append((unique_id, json_data_string))

        # [중요] 중복 ID 제거
        # CSV 파일 자체에 'Q1'이 여러 번 정의된 오류가 있을 경우,
        # ON CONFLICT 오류를 방지하기 위해 딕셔너리로 변환하여 중복을 제거합니다.
        # (딕셔너리의 키는 중복될 수 없으므로, 마지막 값으로 덮어써짐)
        unique_data_dict = {d[0]: d[1] for d in data_to_insert}
        data_to_insert = [(k, v) for k, v in unique_data_dict.items()]

        if data_to_insert:
            cur = conn.cursor()
            try:
                # INSERT ... ON CONFLICT (codebook_id) DO UPDATE SET ...
                # codebook_id(PK)가 이미 존재하면(qpoll에서 삽입됨) 덮어쓰고,
                # 없으면 새로 삽입합니다. (멱등성 보장)
                insert_query = f"""
                INSERT INTO {CODEBOOKS_TABLE} (codebook_id, codebook_data)
                VALUES %s
                ON CONFLICT (codebook_id) DO UPDATE SET
                    codebook_data = EXCLUDED.codebook_data;
                """
                # execute_values로 중복 제거된 데이터를 대량 삽입
                execute_values(cur, insert_query, data_to_insert)
                conn.commit()
                print(f"  [Stage 1] 코드북 데이터 {len(data_to_insert)}건 저장 완료.")
            except Exception as e:
                print(f"  XXX [Stage 1] 코드북 DB 삽입 중 오류 발생: {e}")
                conn.rollback()
            finally:
                cur.close()

        return True

    except Exception as e:
        print(f"  XXX [Stage 1] 코드북 파일 처리 중 오류 발생: {e}")
        return False


# --- 7. Welcome 2nd 데이터 ETL 함수 (Pass 2) ---
def process_data_etl(conn, file_path, prefix):
    """'wel_2ndex.csv' 파일을 파싱하여 respondents, answers 테이블에 삽입합니다."""
    print(f"  [Stage 2] '{file_path}'의 Welcome 2nd 데이터 처리 시작 (Prefix: {prefix})...")
    
    respondents_to_insert = set() # respondents 테이블용 (중복 제거)
    answers_to_insert = [] # answers 테이블용 (대량 삽입)
    
    try:
        # CSV 읽기 (UTF-8 시도 -> 실패 시 CP949)
        try:
            df_panel = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df_panel = pd.read_csv(file_path, encoding='cp949')

        mb_sn_col_name = 'mb_sn' # Welcome 2nd는 'mb_sn'으로 고정
        if mb_sn_col_name not in df_panel.columns:
            print(f"  XXX [Stage 2] 오류: '{mb_sn_col_name}' ID 컬럼이 없습니다. 건너뜁니다.")
            return False

        print("  [Stage 2] 데이터 변환(Unpivot, 콤마 분리) 시작...")
        
        # Pandas DataFrame을 한 줄(row)씩 순회
        for row in df_panel.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리(컬럼명: 값)로 변환
            mb_sn = str(row_dict.get(mb_sn_col_name, '')).strip()
            
            if not mb_sn: continue # mb_sn 없는 행 무시
            
            # (1) respondents 테이블 데이터 추출
            respondents_to_insert.add((mb_sn,)) # set에 추가 (자동 중복 제거)

            # (2) metadata 테이블 처리는 이 스크립트에서 생략

            # (3) answers 테이블 데이터 추출 (Unpivot 과정)
            # 딕셔너리의 (key, value) 쌍을 순회 (key='Q1', value='1')
            for question_id, raw_answer_value in row_dict.items():
                
                # ID 컬럼이거나, 값이 비어있으면(NaN) 건너뜀
                if (question_id == mb_sn_col_name or pd.isna(raw_answer_value)): 
                    continue
                
                # codebooks 테이블과 일치하는 unique_id 생성 (e.g., 'w2_Q1')
                unique_question_id = f"{prefix}{question_id}"
                answer_string = str(raw_answer_value).strip()
                if not answer_string: continue # 빈 문자열 무시

                # 콤마(,)로 구분된 다중 응답 처리 (e.g., "1, 3, 4")
                # '1,3,4' -> ['1', '3', '4']
                split_values = [val.strip() for val in answer_string.split(',') if val.strip()]

                # 분리된 각 값을 별개의 행으로 answers_to_insert 리스트에 추가
                for final_value in split_values:
                    answers_to_insert.append((mb_sn, unique_question_id, final_value))

        print(f"  [Stage 2] 데이터 변환 완료. {len(respondents_to_insert)}명, {len(answers_to_insert)}개 답변 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # (1) Respondents 삽입
            if respondents_to_insert:
                # 'ON CONFLICT (mb_sn) DO NOTHING':
                #   mb_sn이 이미 (welcome_1st, qpoll에서) 존재하면 무시
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
                
                # [중요] 멱등성: 이 스크립트를 여러 번 실행해도 데이터가 중복되지 않도록,
                # 'w2_' prefix를 가진 기존 답변들을 먼저 삭제합니다.
                # (qpoll('qp_') 데이터는 삭제되지 않습니다.)
                print(f"  [Stage 2] '{ANSWERS_TABLE}' 테이블에서 기존 'w2_' 답변 삭제 중...")
                cur.execute(
                    # 현재 파일에 포함된 mb_sn 리스트에 대해서만 삭제
                    f"DELETE FROM {ANSWERS_TABLE} WHERE mb_sn = ANY(%s) AND question_id LIKE %s;",
                    (respondent_id_list, f"{prefix}%") 
                )

            # Answers 대량 삽입
            if answers_to_insert:
                print(f"  [Stage 2] '{ANSWERS_TABLE}' 테이블에 {len(answers_to_insert)}건 삽입 중...")
                answers_query = f"""
                INSERT INTO {ANSWERS_TABLE} (mb_sn, question_id, answer_value) 
                VALUES %s;
                """
                execute_values(cur, answers_query, answers_to_insert)

            conn.commit() # (1)과 (3) 작업을 DB에 최종 반영
            print(f"  [Stage 2] 패널 데이터가 마스터 DB에 성공적으로 저장되었습니다.")
            return True
            
        except Exception as e:
            print(f"  XXX [Stage 2] 패널 데이터 DB 삽입 중 오류 발생: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()

    except Exception as e:
        print(f"  XXX [Stage 2] 패널 데이터 파일 처리 중 오류 발생: {e}")
        return False


# --- 8. 메인 실행 파이프라인 ---
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

# --- 9. 스크립트 실행 ---
# 'python welcome_2nd_etl.py'로 직접 실행되었을 때만 main() 함수를 호출
if __name__ == '__main__':
    main()
