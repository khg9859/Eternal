# -*- coding: utf-8 -*-
# 필요한 라이브러리들을 임포트합니다.
import psycopg2  # PostgreSQL DB 연결을 위한 라이브러리
from psycopg2.extras import execute_values  # 대량의 데이터를 효율적으로 삽입하기 위한 헬퍼 함수
import pandas as pd  # 엑셀(XLSX) 파일을 읽고 데이터를 다루기 위한 라이브러리
import json  # JSON 데이터를 다루기 위한 라이브러리
import os  # 파일 및 폴더 경로를 다루기 위한 라이브러리
from dotenv import load_dotenv

# from datetime import datetime 

# [안내] 이 스크립트는 pandas에서 XLSX 파일을 읽기 위해 'open_pyxl' 라이브러리가 필요합니다.
# (psycopg2-binary, pandas, openpyxl이 모두 설치되어 있어야 합니다)

# --- 설정 (Configuration) ---
# 스크립트 전역에서 사용될 설정 값들을 정의합니다.

# PostgreSQL 데이터베이스 연결 정보
DB_HOST = os.os.getenv('DB_HOST','localhost') # 데이터베이스 서버 주소
DB_PORT = os.os.getenv('DB_PORT','5432')    # 데이터베이스 포트
DB_NAME = os.os.getenv('DB_NAME')   # 연결할 데이터베이스 이름
DB_USER = os.os.getenv('DB_USER','postgres')   # 데이터베이스 사용자 ID
DB_PASSWORD = os.os.getenv('DB_PASSWORD')  # 데이터베이스 비밀번호 (실제 환경에서는 보안에 유의)

# 원본 XLSX 파일들이 들어있는 폴더 경로
INPUT_FOLDER = 'D:/capstone/Eternal/Data/db_insert/panelData/' 

# 마스터 테이블 이름 정의
RESPONDENTS_TABLE = 'respondents' # 응답자 고유 ID와 프로필 벡터를 저장할 테이블
ANSWERS_TABLE = 'answers'         # 개별 응답 내역을 저장할 테이블 (가장 많은 데이터)
CODEBOOKS_TABLE = 'codebooks'     # 질문의 메타데이터(질문 제목, 보기 등)를 저장할 테이블
METADATA_TABLE = 'metadata'       # 응답자의 고정 프로필(성별, 나이 등)을 저장할 테이블

# qpoll 데이터 시트(Sheet 1)에서 '고유번호'로 사용될 컬럼 이름 후보 목록
ID_CANDIDATES = ['mb_sn', '고유번호', '패널ID', 'id']
# [신규] 'metadata' 테이블에 직접 저장할 (answers 테이블에 넣지 않을) 메타데이터 컬럼 목록
METADATA_COLUMNS = ['구분', '성별', '나이', '지역']
# [신규] ETL 과정에서 무시할 컬럼 목록 (예: 설문 응답 시간이지만 분석에 불필요한 경우)
COLUMNS_TO_IGNORE = ['설문일시']
# [신규] ETL 과정에서 건너뛸 파일 목록
FILES_TO_IGNORE = ['Welcome_1st.xlsx', 'welcome_2nd.xlsx', 'Welcome_1st.csv', 'welcome_1st_codebook.csv']


# --- 1. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
    try:
        # 설정 값을 사용하여 DB 연결을 시도합니다.
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        print(">>> [Phase 1] PostgreSQL DB 연결 성공.")
        return conn  # 연결 객체를 반환합니다.
    except psycopg2.OperationalError as e:
        # 연결 실패 시 오류 메시지를 출력하고 None을 반환합니다.
        print(f"XXX [Phase 1] DB 연결 실패: {e}")
        return None

# --- 2. [수정됨] 4-테이블 마스터 스키마 생성 함수 ---
def setup_master_tables(conn):
    """
    [수정] 마스터 스키마의 4개 테이블이 없으면 생성합니다.
    (Welcome 스크립트와 달리) 기존 테이블을 삭제하지 않고, 없으면 생성(IF NOT EXISTS)만 합니다.
    """
    queries = [
        # 1. respondents 테이블: 응답자(패널)의 고유 ID(PK)와 프로필 벡터를 저장합니다.
        f"""
        CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (
            mb_sn VARCHAR(255) PRIMARY KEY,
            profile_vector TEXT DEFAULT NULL
        );
        """,
        # 2. metadata 테이블: 응답자의 고정 정보(프로필)를 저장합니다.
        f"""
        CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            metadata_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            mobile_carrier VARCHAR(100) DEFAULT NULL,
            gender VARCHAR(10) DEFAULT NULL,
            age VARCHAR(50) DEFAULT NULL, 
            region VARCHAR(100) DEFAULT NULL
        );
        """,
        # 3. codebooks 테이블: 질문 정보(질문 제목, 보기 내용)를 JSONB 형태로 저장합니다.
        f"""
        CREATE TABLE IF NOT EXISTS {CODEBOOKS_TABLE} (
            codebook_id VARCHAR(255) PRIMARY KEY, 
            codebook_data JSONB
        );
        """,
        # 4. answers 테이블: 실제 응답 내역을 저장합니다. (가장 데이터가 많은 테이블)
        f"""
        CREATE TABLE IF NOT EXISTS {ANSWERS_TABLE} (
            answer_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            question_id VARCHAR(255), 
            answer_value TEXT
        );
        """,
        # 5. answers 테이블의 검색 성능 향상을 위한 인덱스를 생성합니다.
        f"""
        CREATE INDEX IF NOT EXISTS idx_answers_respondent ON {ANSWERS_TABLE} (mb_sn);
        """,
        f"""
        CREATE INDEX IF NOT EXISTS idx_answers_question ON {ANSWERS_TABLE} (question_id);
        """
    ]
    
    cur = conn.cursor()  # DB 작업을 위한 커서 생성
    try:
        print(">>> [Phase 2] 마스터 테이블 4개 (respondents, metadata, codebooks, answers) 셋업 완료.")
        
        # 위에서 정의한 모든 CREATE TABLE 쿼리를 실행합니다. (IF NOT EXISTS로 안전하게)
        for query in queries:
            cur.execute(query)
            
        # pgvector 확장 기능이 활성화되어 있지 않다면 활성화합니다. (필요 시)
        # cur.execute("CREATE EXTENSION IF NOT EXISTS vector;") 
        
        conn.commit()  # 모든 스키마 변경 사항을 DB에 최종 반영(커밋)
        return True
    except Exception as e:
        print(f"XXX [Phase 2] 테이블 설정 중 오류 발생: {e}")
        conn.rollback()  # 오류 발생 시 모든 변경 사항을 되돌립니다(롤백).
        return False
    finally:
        cur.close()  # 커서를 닫습니다.

# --- 3. [신규] 헬퍼 함수 (데이터 변환용) ---

# [수정] qpoll의 '나이'는 '39'와 같은 원본 값을 사용하므로, calculate_age_format 함수 제거

def map_gender(gender_raw):
    """ [수정] qpoll의 '남'/'여'를 '남성'/'여성'으로 변환합니다. """
    gender_str = str(gender_raw).strip() # qpoll은 '남', '여' 사용
    if gender_str == '남':
        return '남성'
    elif gender_str == '여':
        return '여성'
    return gender_raw # '남', '여'가 아니면 원본 반환 (e.g., '남성'이 이미 입력된 경우)

# --- 4. Stage 1: qpoll 코드북 ETL (수평 파서) ---
def process_codebook_etl(conn, file_path, prefix):
    """qpoll의 '수평' 형식 코드북(Sheet 2, header=0)을 파싱하여 DB에 삽입합니다."""
    print(f"  [Stage 1] '{file_path}'의 qpoll 코드북(Sheet 2) 처리 시작 (Prefix: {prefix})...")
    
    try:
        # "두 번째 시트"(index 1)를 읽음, "첫 번째 줄"(header=0)을 헤더로 사용
        df_codebook = pd.read_excel(file_path, sheet_name=1, engine='openpyxl', header=0)
        
        codebook_dict = {} 

        # 시트의 모든 행 (각 행 = 질문 1개)을 순회
        for row in df_codebook.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리로 변환
            
            # '설문제목' 컬럼 값을 질문 제목이자 ID로 사용
            q_title = str(row_dict.get('설문제목', '')).strip()
            if not q_title:
                continue
                
            # 메타데이터 컬럼이나 ID 후보 컬럼과 겹치는지 확인
            if q_title in METADATA_COLUMNS or q_title in ID_CANDIDATES:
                continue

            cleaned_q_title = q_title.replace('\n', ' ')
            # codebooks 테이블과 일치하는 unique_id 생성
            unique_id = f"{prefix}{cleaned_q_title}"
            answers = [] # 보기 정보를 저장할 리스트
            
            # '보기1'부터 '보기10'까지 (최대 10개로 가정) 순회
            max_options = 10 
            for i in range(1, max_options + 1):
                qi_title_key = f'보기{i}'
                qi_title = str(row_dict.get(qi_title_key, '')).strip()
                qi_val = str(i) 
                
                if qi_title and pd.notna(row_dict.get(qi_title_key)):
                    answers.append({"qi_val": qi_val, "qi_title": qi_title})

            # DB에 저장할 JSON 객체 생성
            codebook_obj = {
                "codebook_id": unique_id,
                "q_title": q_title, # 원본 질문 제목 (개행 문자 포함)을 저장
                "answers": answers
            }
            
            codebook_dict[unique_id] = codebook_obj
        
        print(f"  [Stage 1] 코드북 파싱 완료. {len(codebook_dict)}개의 '실제 질문' 항목 감지.")
        
        # --- DB에 삽입 ---
        data_to_insert = [] # DB에 일괄 삽입(batch insert)할 데이터를 담을 리스트
        for unique_id, codebook_obj in codebook_dict.items():
            json_data_string = json.dumps(codebook_obj, ensure_ascii=False)
            data_to_insert.append((unique_id, json_data_string))
            
        if data_to_insert: # 삽입할 데이터가 있을 경우에만 실행
            cur = conn.cursor()
            try:
                # INSERT ... ON CONFLICT ... DO UPDATE:
                insert_query = f"""
                INSERT INTO {CODEBOOKS_TABLE} (codebook_id, codebook_data)
                VALUES %s
                ON CONFLICT (codebook_id) DO UPDATE SET
                    codebook_data = EXCLUDED.codebook_data;
                """
                execute_values(cur, insert_query, data_to_insert)
                conn.commit() # DB에 최종 반영
            except Exception as e:
                print(f"  XXX [Stage 1] 코드북 DB 삽입 중 오류 발생: {e}")
                conn.rollback() # 오류 시 롤백
            finally:
                cur.close()
        return True

    except Exception as e:
        print(f"  XXX [Stage 1] 코드북 시트 처리 중 오류 발생: {e}")
        return False

# --- 5. Stage 2: [수정됨] qpoll 패널 데이터 ETL (메타데이터 분리) ---
def process_data_etl(conn, file_path, prefix):
    """XLSX 파일의 *첫 번째 시트(header=1)*를 파싱하여 respondents, metadata, answers로 분리 삽입합니다."""
    print(f"  [Stage 2] '{file_path}'의 패널 데이터(Sheet 1, Header 2번째줄) 처리 시작 (Prefix: {prefix})...")
    
    respondents_to_insert = set() 
    metadata_to_insert_dict = {} 
    answers_to_insert = []    
    
    try:
        # --- [ID 매핑 수정] ---
        # 1. 엑셀 파일의 첫 번째 줄(header=None, nrows=1)을 읽어와서 값 리스트로 만듭니다.
        df_titles_row = pd.read_excel(file_path, sheet_name=0, engine='openpyxl', header=None, nrows=1)
        title_values = df_titles_row.iloc[0].values.tolist()

        # [수정] "Forward Fill" 로직: 병합된 셀(NaN)을 바로 앞의 유효한 제목으로 채웁니다.
        last_title = ''
        title_columns = []
        for val in title_values:
            if pd.notna(val) and not str(val).startswith('Unnamed'):
                last_title = str(val).strip().replace('\n', ' ')
            title_columns.append(last_title)
        
        # 2. 엑셀 파일의 두 번째 줄(header=1)을 읽어와서 실제 데이터프레임으로 사용합니다.
        df_panel = pd.read_excel(file_path, sheet_name=0, engine='openpyxl', header=1)
        panel_columns = [str(col).strip() for col in df_panel.columns]
        df_panel.columns = panel_columns # 공백 제거된 컬럼명으로 다시 설정

        # 3. 두 헤더 리스트를 이용해 매핑 딕셔너리를 생성합니다.
        question_id_map = {
            panel_col: title_col 
            for panel_col, title_col in zip(panel_columns, title_columns)
            if panel_col not in ID_CANDIDATES and panel_col not in METADATA_COLUMNS and panel_col not in COLUMNS_TO_IGNORE
        }
        
        header = panel_columns # 헤더는 두 번째 줄(df_panel)의 컬럼을 사용

        # ID_CANDIDATES 목록을 순회하며 실제 파일에서 사용된 '고유번호' 컬럼명을 찾음
        mb_sn_col_name = None
        for candidate in ID_CANDIDATES:
            if candidate in header:
                mb_sn_col_name = candidate
                break
            
        if mb_sn_col_name is None: # ID 컬럼을 찾지 못하면 처리 중단
            print(f"  XXX [Stage 2] 오류: ID 컬럼({', '.join(ID_CANDIDATES)})이 없습니다. 건너뜁니다.")
            return False
        
        print(f"  [Stage 2] ID 컬럼 '{mb_sn_col_name}'을(를) mb_sn 기준으로 사용합니다.")

        # --- 데이터 변환 (Unpivot 및 콤마 분리) ---
        print("  [Stage 2] 데이터 변환(메타데이터 분리, Unpivot, 콤마 분리) 시작...")
        
        # Pandas DataFrame을 한 줄(row)씩 순회
        for row in df_panel.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리로 변환 (컬럼명: 값)
            mb_sn = str(row_dict.get(mb_sn_col_name, '')).strip() # 고유번호 추출
            
            if not mb_sn: continue # 고유번호가 없는 행은 무시
            
            # (1) respondents 테이블 데이터 추출: set에 추가 (자동으로 중복 제거됨)
            respondents_to_insert.add((mb_sn,)) 

            # (2) metadata 테이블 데이터 추출
            # [수정] qpoll의 '구분' 컬럼을 mobile_carrier 변수에 저장
            mobile_carrier = str(row_dict.get('구분', '') or '').strip() 
            
            # [수정] gender 변환 로직 적용 (qpoll의 '성별' 컬럼 사용)
            gender_raw = str(row_dict.get('성별', '') or '').strip()
            gender = map_gender(gender_raw)
            
            # [수정] age 변환 로직 제거 (qpoll의 '나이'는 원본 '39' '40' 등을 그대로 사용)
            age = str(row_dict.get('나이', '') or '').strip()
            
            # [수정] qpoll의 '지역' 컬럼은 1개이므로 조합 필요 없음
            region = str(row_dict.get('지역', '') or '').strip()
            
            # dict에 (mb_sn, mobile_carrier, ...) 형태로 저장 (중복 ID는 덮어쓰기)
            metadata_to_insert_dict[mb_sn] = (mb_sn, mobile_carrier, gender, age, region)

            # (3) answers 테이블 데이터 추출 (Unpivot 과정)
            for question_id, raw_answer_value in row_dict.items():
                
                # 이 컬럼이 ID, 메타데이터, 무시 목록에 포함되거나, 값이 비어있으면(NaT) 건너뜀
                if (question_id in ID_CANDIDATES or 
                    question_id in METADATA_COLUMNS or 
                    question_id in COLUMNS_TO_IGNORE or
                    pd.isna(raw_answer_value)): 
                    continue
                
                real_question_id = question_id_map.get(question_id)
                
                if not real_question_id:
                    continue
                    
                unique_question_id = f"{prefix}{real_question_id}"
                answer_string = str(raw_answer_value).strip() # 응답 값을 문자열로 변환
                if not answer_string: continue # 빈 값 무시

                # 콤마(,)로 구분된 다중 응답 처리 (예: "1, 3, 4")
                split_values = [val.strip() for val in answer_string.split(',') if val.strip()]

                for final_value in split_values:
                    answers_to_insert.append((mb_sn, unique_question_id, final_value))

        metadata_to_insert_list = list(metadata_to_insert_dict.values())

        print(f"  [Stage 2] 데이터 변환 완료. {len(respondents_to_insert)}명, {len(metadata_to_insert_list)}개 메타데이터, {len(answers_to_insert)}개 답변 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # (1) Respondents 삽입
            if respondents_to_insert:
                respondents_query = f"""
                INSERT INTO {RESPONDENTS_TABLE} (mb_sn) 
                VALUES %s 
                ON CONFLICT (mb_sn) DO NOTHING; 
                """ # mb_sn(PK)이 이미 존재하면(다른 파일에서 이미 삽입됨) 무시
                execute_values(cur, respondents_query, list(respondents_to_insert))
            
            # (2) [신규] Metadata 삽입/업데이트
            if metadata_to_insert_list:
                # [수정] Welcome 스크립트와 동일한 COALESCE 로직 적용
                metadata_query = f"""
                INSERT INTO {METADATA_TABLE} (mb_sn, mobile_carrier, gender, age, region) 
                VALUES %s 
                ON CONFLICT (mb_sn) DO UPDATE SET
                    mobile_carrier = COALESCE({METADATA_TABLE}.mobile_carrier, EXCLUDED.mobile_carrier),
                    gender = COALESCE({METADATA_TABLE}.gender, EXCLUDED.gender),
                    age = COALESCE({METADATA_TABLE}.age, EXCLUDED.age),
                    region = COALESCE({METADATA_TABLE}.region, EXCLUDED.region);
                """ 
                execute_values(cur, metadata_query, metadata_to_insert_list)
            
            # (3) Answers 삽입 (기존 데이터 삭제 후 삽입 - 멱등성 보장)
            respondent_ids_in_this_file = list(respondents_to_insert) 
            if respondent_ids_in_this_file:
                # 현재 파일의 ID 목록 (mb_sn,) 튜플의 리스트이므로, [r[0] for r in ...]로 ID만 추출
                respondent_id_list = [r[0] for r in respondent_ids_in_this_file]
                
                # [중요] 현재 파일의 prefix (예: 'qp250106_')로 시작하는 답변만 삭제합니다.
                cur.execute(
                    f"DELETE FROM {ANSWERS_TABLE} WHERE mb_sn = ANY(%s) AND question_id LIKE %s;",
                    (respondent_id_list, f"{prefix}%") 
                )

            if answers_to_insert:
                answers_query = f"""
                INSERT INTO {ANSWERS_TABLE} (mb_sn, question_id, answer_value) 
                VALUES %s;
                """ # 외래 키 제약이 없으므로 execute_values로 빠르게 삽입
                execute_values(cur, answers_query, answers_to_insert)

            conn.commit() # (1), (2), (3)의 모든 DB 작업을 최종 반영
            print(f"  [Stage 2] 패널 데이터가 마스터 DB에 성공적으로 저장되었습니다.")
            return True
            
        except Exception as e:
            print(f"  XXX [Stage 2] 패널 데이터 DB 삽입 중 오류 발생: {e}")
            conn.rollback() # 오류 발생 시 이 파일에 대한 모든 작업을 롤백
            return False
        finally:
            cur.close()

    except Exception as e:
        print(f"  XXX [Stage 2] 패널 데이터 시트 처리 중 오류 발생: {e}")
        return False


# --- 6. 메인 실행 파이프라인 ---
def main():
    db_conn = connect_to_db() # 1. DB 연결
    if db_conn:
        try:
            # 2. DB 스키마(테이블) 설정 (IF NOT EXISTS)
            if not setup_master_tables(db_conn):
                print("오류: 마스터 테이블 생성에 실패하여 ETL을 중단합니다.")
                db_conn.close()
                return # 스키마 생성 실패 시 즉시 종료
            
            print(f">>> [Phase 3] 입력 폴더 '{INPUT_FOLDER}' 스캔 시작...")
            try:
                # 'qpoll_join_'으로 시작하고 '.xlsx'로 끝나는 파일만 대상으로 함
                all_files = os.listdir(INPUT_FOLDER)
                files_to_process = [
                    f for f in all_files 
                    if f.startswith('qpoll_join_') 
                    and f.endswith('.xlsx') 
                    and not f.startswith('~')
                    and f not in FILES_TO_IGNORE # [신규] 무시 목록에 없는 파일만
                ]
                
                # [신규] 무시된 파일 목록 로그
                ignored_files = [f for f in all_files if f in FILES_TO_IGNORE]
                for f in ignored_files:
                    print(f"  [Info] 건너뛰는 파일: '{f}'")

            except FileNotFoundError:
                print(f"XXX 오류: '{INPUT_FOLDER}' 폴더를 찾을 수 없습니다.")
                files_to_process = []

            if not files_to_process:
                print(">>> [Phase 4] 처리할 'qpoll_join_' .xlsx 파일이 없습니다.")
            else:
                print(f">>> [Phase 4] qpoll 파일 ({len(files_to_process)}개) 처리 시작...")

            # 2-Pass Loop (2중 루프):
            
            # Pass 1: 모든 코드북을 먼저 삽입 (Sheet 2 처리)
            print("\n--- ETL Pass 1: 모든 코드북 처리 시작 ---")
            for i, file_name in enumerate(files_to_process):
                file_path = os.path.join(INPUT_FOLDER, file_name)
                # 파일명에서 접두어(prefix) 생성 (예: 'qpoll_join_250106' -> 'qp250106_')
                prefix_base = os.path.splitext(file_name)[0].replace('qpoll_join_', 'qp') 
                prefix = f"{prefix_base}_" 
                
                print(f"\n--- [File {i+1}/{len(files_to_process)}] '{file_name}' 처리 중 ---")
                process_codebook_etl(db_conn, file_path, prefix) # Stage 1 함수 호출
            print("\n--- ETL Pass 1: 모든 코드북 처리 완료 ---")

            # Pass 2: 모든 패널 데이터를 삽입 (Sheet 1 처리)
            print("\n--- ETL Pass 2: 모든 패널 데이터 처리 시작 ---")
            for i, file_name in enumerate(files_to_process):
                file_path = os.path.join(INPUT_FOLDER, file_name)
                prefix_base = os.path.splitext(file_name)[0].replace('qpoll_join_', 'qp')
                prefix = f"{prefix_base}_"
                
                print(f"\n--- [File {i+1}/{len(files_to_process)}] '{file_name}' 처리 중 ---")
                process_data_etl(db_conn, file_path, prefix) # Stage 2 함수 호출
            print("\n--- ETL Pass 2: 모든 패널 데이터 처리 완료 ---")

            print("\n>>> [Phase 5] 모든 ETL 작업이 완료되었습니다.")

        except Exception as e:
            print(f"XXX 메인 실행 중 오류 발생: {e}")
            db_conn.rollback() # 메인 파이프라인에서 예외 발생 시 롤백
        finally:
            db_conn.close() # 모든 작업이 끝나면 DB 연결 종료
            print(">>> [Phase 6] PostgreSQL DB 연결 종료.")

# --- 스크립트 실행 ---
if __name__ == '__main__':
    main()

