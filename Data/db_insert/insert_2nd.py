# -*- coding: utf-8 -*-
# Welcome 2nd ETL 스크립트
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import json
import os
from dotenv import load_dotenv


# --- 설정 (Configuration) ---
DB_HOST = os.getenv('DB_HOST','localhost') # 데이터베이스 서버 주소 ##보안을 신경 쓰지 않으면 = DB_HOST='' 식으로 사용가능
DB_PORT = os.getenv('DB_PORT','5432')    # 데이터베이스 포트
DB_NAME = os.getenv('DB_NAME')   # 연결할 데이터베이스 이름
DB_USER = os.getenv('DB_USER','postgres')   # 데이터베이스 사용자 ID
DB_PASSWORD = os.getenv('DB_PASSWORD')  # 데이터베이스 비밀번호 (실제 환경에서는 보안에 유의)

INPUT_FOLDER = 'D:/capstone/Eternal/Data/db_insert/panelData/'
DATA_FILE = 'wel_2ndex.csv'
CODEBOOK_FILE = 'welcome_2nd_codebook.csv'
PREFIX = 'w2_' # Welcome 2nd의 고유 접두사

# 마스터 테이블 이름 정의
RESPONDENTS_TABLE = 'respondents'
ANSWERS_TABLE = 'answers'
CODEBOOKS_TABLE = 'codebooks'

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

# --- 2. 마스터 테이블 확인 함수 ---
def setup_master_tables(conn):
    """
    [수정] 마스터 스키마의 4개 테이블이 없으면 생성합니다.
    (Welcome 스크립트와 달리) 기존 테이블을 삭제하지 않고, 없으면 생성(IF NOT EXISTS)만 합니다.
    """
    queries = [
        f"CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (mb_sn VARCHAR(255) PRIMARY KEY, profile_vector TEXT DEFAULT NULL);",
        f"""CREATE TABLE IF NOT EXISTS metadata (
            metadata_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            mobile_carrier VARCHAR(100) DEFAULT NULL,
            gender VARCHAR(10) DEFAULT NULL,
            age VARCHAR(50) DEFAULT NULL, 
            region VARCHAR(100) DEFAULT NULL
        );""",
        f"CREATE TABLE IF NOT EXISTS {CODEBOOKS_TABLE} (codebook_id VARCHAR(255) PRIMARY KEY, codebook_data JSONB);",
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

def process_codebook_etl(conn, file_path, prefix):
    """'welcome_2nd_codebook.csv' (수직 형식) 코드북을 파싱하여 DB에 삽입합니다."""
    print(f"  [Stage 1] '{file_path}'의 Welcome 2nd 코드북 처리 시작 (Prefix: {prefix})...")

    try:
        # CSV 읽기
        try:
            df_codebook = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df_codebook = pd.read_csv(file_path, encoding='cp949')

        codebook_objects = []
        current_question_id = None
        current_question_title = None
        current_answers = []

        # CSV를 한 줄씩 순회
        for row in df_codebook.itertuples(index=False):
            var_name = str(row[0]).strip()  # 변수명 (e.g., Q1)
            question_text = str(row[1]).strip()  # 문항 (e.g., 결혼여부 or 1)
            question_type = str(row[2]).strip()  # 문항유형 (e.g., SINGLE or 미혼)

            # 새로운 질문 시작
            if pd.notna(row[0]) and var_name:
                if current_question_id:
                    obj = {
                        "codebook_id": f"{prefix}{current_question_id}",
                        "q_title": current_question_title,
                        "answers": current_answers
                    }
                    codebook_objects.append(obj)

                current_question_id = var_name
                current_question_title = question_text
                current_answers = []

            # 보기 항목 처리
            elif pd.notna(row[1]) and pd.notna(row[2]):
                qi_val = question_text
                qi_title = question_type

                if qi_val.isdigit() and qi_title not in ('SINGLE', 'Numeric', 'String', 'nan'):
                    current_answers.append({"qi_val": qi_val, "qi_title": qi_title})

        # 마지막 질문 저장
        if current_question_id:
            obj = {
                "codebook_id": f"{prefix}{current_question_id}",
                "q_title": current_question_title,
                "answers": current_answers
            }
            codebook_objects.append(obj)

        print(f"  [Stage 1] 코드북 파싱 완료. {len(codebook_objects)}개의 질문 항목 감지.")

        # --- DB에 삽입 ---
        data_to_insert = []
        for codebook_obj in codebook_objects:
            if codebook_obj["codebook_id"] == f"{prefix}mb_sn":
                continue
            unique_id = codebook_obj["codebook_id"]
            json_data_string = json.dumps(codebook_obj, ensure_ascii=False)
            data_to_insert.append((unique_id, json_data_string))

        # 중복 제거 (마지막 값으로 덮어쓰기)
        unique_data_dict = {d[0]: d[1] for d in data_to_insert}
        data_to_insert = [(k, v) for k, v in unique_data_dict.items()]

        if data_to_insert:
            cur = conn.cursor()
            try:
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


# --- 4. [신규] Welcome 2nd 데이터 ETL ---
def process_data_etl(conn, file_path, prefix):
    """'welcome_2nd.xlsx - data.csv' 파일을 파싱하여 respondents, answers 테이블에 삽입합니다."""
    print(f"  [Stage 2] '{file_path}'의 Welcome 2nd 데이터 처리 시작 (Prefix: {prefix})...")
    
    respondents_to_insert = set() 
    answers_to_insert = []    
    
    try:
        try:
            df_panel = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df_panel = pd.read_csv(file_path, encoding='cp949')

        mb_sn_col_name = 'mb_sn' # Welcome 2nd는 'mb_sn'으로 고정
        if mb_sn_col_name not in df_panel.columns:
            print(f"  XXX [Stage 2] 오류: '{mb_sn_col_name}' ID 컬럼이 없습니다. 건너뜁니다.")
            return False

        print("  [Stage 2] 데이터 변환(Unpivot, 콤마 분리) 시작...")
        
        # Pandas DataFrame을 한 줄(row)씩 순회
        for row in df_panel.itertuples(index=False):
            row_dict = row._asdict()
            mb_sn = str(row_dict.get(mb_sn_col_name, '')).strip()
            
            if not mb_sn: continue
            
            # (1) respondents 테이블 데이터 추출
            respondents_to_insert.add((mb_sn,)) 

            # (2) metadata 테이블 처리는 생략 (요청 사항)

            # (3) answers 테이블 데이터 추출 (Unpivot 과정)
            for question_id, raw_answer_value in row_dict.items():
                
                # ID 컬럼이거나, 값이 비어있으면 건너뜀
                if (question_id == mb_sn_col_name or pd.isna(raw_answer_value)): 
                    continue
                
                # codebooks 테이블과 일치하는 unique_id 생성 (e.g., 'w2_Q1')
                unique_question_id = f"{prefix}{question_id}"
                answer_string = str(raw_answer_value).strip()
                if not answer_string: continue

                # 콤마(,)로 구분된 다중 응답 처리 (e.g., "1, 3, 4")
                split_values = [val.strip() for val in answer_string.split(',') if val.strip()]

                for final_value in split_values:
                    answers_to_insert.append((mb_sn, unique_question_id, final_value))

        print(f"  [Stage 2] 데이터 변환 완료. {len(respondents_to_insert)}명, {len(answers_to_insert)}개 답변 감지.")

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

            # (3) Answers 삽입 (기존 데이터 삭제 후 삽입)
            respondent_ids_in_this_file = list(respondents_to_insert) 
            if respondent_ids_in_this_file:
                respondent_id_list = [r[0] for r in respondent_ids_in_this_file]
                
                # [중요] 현재 파일의 prefix (w2_)로 시작하는 답변만 삭제
                print(f"  [Stage 2] '{ANSWERS_TABLE}' 테이블에서 기존 'w2_' 답변 삭제 중...")
                cur.execute(
                    f"DELETE FROM {ANSWERS_TABLE} WHERE mb_sn = ANY(%s) AND question_id LIKE %s;",
                    (respondent_id_list, f"{prefix}%") 
                )

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


# --- 5. 메인 실행 파이프라인 ---
def main():
    db_conn = connect_to_db()
    if db_conn:
        try:
            if not setup_master_tables(db_conn):
                print("오류: 마스터 테이블 셋업에 실패하여 ETL을 중단합니다.")
                db_conn.close()
                return
            
            print(f">>> [Phase 3] Welcome 2nd 파일 처리 시작...")
            
            codebook_path = os.path.join(INPUT_FOLDER, CODEBOOK_FILE)
            data_path = os.path.join(INPUT_FOLDER, DATA_FILE)
            
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
            db_conn.close()
            print(">>> [Phase 5] PostgreSQL DB 연결 종료.")

# --- 스크립트 실행 ---
if __name__ == '__main__':
    main()
