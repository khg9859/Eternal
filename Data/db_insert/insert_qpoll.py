# -*- coding: utf-8 -*-
"""
Qpoll ETL 스크립트 (Append-Only 버전)

이 스크립트는 'qpoll_join_*.xlsx' 엑셀 파일들을 읽어와서
PostgreSQL 데이터베이스의 'respondents', 'metadata', 'codebooks', 'answers'
4개 테이블에 데이터를 삽입(Append)합니다.

[중요] 이 스크립트는 'metadata' 테이블을 채웁니다. (welcome_1st와 데이터 병합)

주요 기능:
1. .env 파일을 통해 DB 접속 정보를 안전하게 로드합니다.
2. 4개의 마스터 테이블이 없으면 생성합니다. (IF NOT EXISTS)
   - [중요] 기존 데이터를 보존하기 위해 테이블을 삭제(DROP)하지 않습니다.
3. qpoll 엑셀의 'Sheet 2' (수평 형식 코드북)를 파싱하여 'codebooks' 테이블에 삽입합니다.
4. qpoll 엑셀의 'Sheet 1' (2-헤더 데이터 시트)을 파싱하여 'respondents', 'metadata', 'answers' 테이블에 삽입합니다.
5. 'qp' 접두사(prefix)를 사용하여 다른 데이터 소스(welcome_2nd)와 ID가 충돌하지 않도록 합니다.
6. 'welcome_1st'에서 변환한 '남성'/'여성'과 일치하도록, qpoll의 '남'/'여'를 '남성'/'여성'으로 변환합니다.
"""

# --- 1. 라이브러리 임포트 ---
import psycopg2 # PostgreSQL DB 어댑터
from psycopg2.extras import execute_values # 대량 INSERT를 위한 psycopg2 헬퍼
import pandas as pd # 데이터 분석 및 엑셀(XLSX) 파일 읽기용 라이브러리
import json # 코드북 데이터를 JSON 문자열로 변환하기 위함
import os # .env 값(환경 변수)을 읽고, 파일 경로를 다루기 위함
from dotenv import load_dotenv,find_dotenv  # .env 파일에서 환경 변수를 로드하기 위함

# from datetime import datetime # (qpoll은 '나이'를 직접 사용하므로 datetime 불필요)

# [안내] 이 스크립트는 pandas에서 XLSX 파일을 읽기 위해 'open_pyxl' 라이브러리가 필요합니다.
# (pip install psycopg2-binary pandas openpyxl)

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

# 마스터 테이블 이름 정의
RESPONDENTS_TABLE = 'respondents' 
ANSWERS_TABLE = 'answers' 
CODEBOOKS_TABLE = 'codebooks' 
METADATA_TABLE = 'metadata' 

# qpoll 데이터 시트(Sheet 1)에서 '고유번호'로 사용될 컬럼 이름 후보 목록
ID_CANDIDATES = ['mb_sn', '고유번호', '패널ID', 'id']
# 'metadata' 테이블에 직접 저장할 (answers 테이블에 넣지 않을) 메타데이터 컬럼 목록
METADATA_COLUMNS = ['구분', '성별', '나이', '지역']
# ETL 과정에서 무시할 컬럼 목록 (예: 설문 응답 시간이지만 분석에 불필요한 경우)
COLUMNS_TO_IGNORE = ['설문일시']
# [신규] ETL 과정에서 건너뛸 특정 파일 목록 (Welcome 파일 등)
FILES_TO_IGNORE = ['Welcome_1st.xlsx', 'welcome_2nd.xlsx', 'Welcome_1st.csv', 'welcome_1st_codebook.csv', 'wel_1st.ex.csv', 'wel_2ndex.csv', 'welcome_2nd_codebook.csv']


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
    queries = [
        # 1. respondents (모든 스크립트가 동일한 구조 사용)
        f"CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (mb_sn VARCHAR(255) PRIMARY KEY, profile_vector TEXT DEFAULT NULL);",
        # 2. metadata (모든 스크립트가 동일한 구조 사용)
        f"""CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            metadata_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            mobile_carrier VARCHAR(100) DEFAULT NULL,
            gender VARCHAR(10) DEFAULT NULL,
            age VARCHAR(50) DEFAULT NULL, 
            region VARCHAR(100) DEFAULT NULL
        );""",
        # 3. codebooks (모든 스크립트가 동일한 구조 사용)
        f"CREATE TABLE IF NOT EXISTS {CODEBOOKS_TABLE} (codebook_id VARCHAR(255) PRIMARY KEY, codebook_data JSONB);",
        # 4. answers (모든 스크립트가 동일한 구조 사용)
        f"""CREATE TABLE IF NOT EXISTS {ANSWERS_TABLE} (
            answer_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            question_id VARCHAR(255), 
            answer_value TEXT
        );""",
        # 5. answers 테이블의 검색 성능 향상을 위한 인덱스 생성 (없으면)
        f"CREATE INDEX IF NOT EXISTS idx_answers_respondent ON {ANSWERS_TABLE} (mb_sn);",
        f"CREATE INDEX IF NOT EXISTS idx_answers_question ON {ANSWERS_TABLE} (question_id);"
    ]
    
    cur = conn.cursor()
    try:
        print(">>> [Phase 2] 마스터 테이블 4개 (respondents, metadata, codebooks, answers) 셋업 확인...")
        
        # 위에서 정의한 모든 CREATE 쿼리를 실행 (IF NOT EXISTS로 안전하게)
        for query in queries:
            cur.execute(query)
            
        # (임베딩 스크립트가 pgvector를 생성하므로 여기서는 주석 처리)
        # cur.execute("CREATE EXTENSION IF NOT EXISTS vector;") 
        
        conn.commit() 
        return True
    except Exception as e:
        print(f"XXX [Phase 2] 테이블 설정 중 오류 발생: {e}")
        conn.rollback() 
        return False
    finally:
        cur.close()

# --- 6. 헬퍼 함수 (데이터 변환용) ---

def map_gender(gender_raw):
    """ [qpoll 전용] '남'/'여'를 '남성'/'여성'으로 변환합니다. """
    gender_str = str(gender_raw).strip() # qpoll은 '남', '여' 사용
    if gender_str == '남':
        return '남성'
    elif gender_str == '여':
        return '여성'
    return gender_raw # '남', '여'가 아니면(예: welcome_1st의 '남성') 원본 유지

# --- 7. Stage 1: qpoll 코드북 ETL (Pass 1) ---
def process_codebook_etl(conn, file_path, prefix):
    """qpoll의 '수평' 형식 코드북(Sheet 2, header=0)을 파싱하여 DB에 삽입합니다."""
    print(f"  [Stage 1] '{file_path}'의 qpoll 코드북(Sheet 2) 처리 시작 (Prefix: {prefix})...")
    
    try:
        # "두 번째 시트"(index 1)를 읽음, "첫 번째 줄"(header=0)을 헤더로 사용
        df_codebook = pd.read_excel(file_path, sheet_name=1, engine='openpyxl', header=0)
        
        # 중복된 질문 ID(q_title)를 덮어쓰기 위해 딕셔너리 사용
        codebook_dict = {} 

        # 시트의 모든 행 (각 행 = 질문 1개)을 순회
        for row in df_codebook.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리로 변환
            
            # '설문제목' 컬럼 값을 질문 제목이자 ID로 사용
            q_title = str(row_dict.get('설문제목', '')).strip()
            if not q_title:
                continue # 질문 제목이 없으면 무시
                
            # '설문제목'이 '성별', '나이' 등 메타데이터 컬럼명이면 무시
            if q_title in METADATA_COLUMNS or q_title in ID_CANDIDATES:
                continue

            # \n (개행 문자)가 ID에 포함되는 것을 방지
            cleaned_q_title = q_title.replace('\n', ' ')
            # codebooks 테이블과 일치하는 unique_id 생성 (예: 'qp250106_체력 관리')
            unique_id = f"{prefix}{cleaned_q_title}"
            answers = [] # 보기 정보를 저장할 리스트
            
            # '보기1'부터 '보기10'까지 (최대 10개로 가정) 순회
            max_options = 10 
            for i in range(1, max_options + 1):
                qi_title_key = f'보기{i}' # '보기1', '보기2', ...
                qi_title = str(row_dict.get(qi_title_key, '')).strip() # '보기1'의 값 (예: '헬스')
                qi_val = str(i) # 보기 값 (예: '1')
                
                # '보기n' 컬럼에 유효한 텍스트가 있을 경우에만
                if qi_title and pd.notna(row_dict.get(qi_title_key)):
                    answers.append({"qi_val": qi_val, "qi_title": qi_title})

            # DB에 저장할 JSON 객체 생성
            codebook_obj = {
                "codebook_id": unique_id,
                "q_title": q_title, # (벡터 임베딩용) 원본 질문 제목 저장
                "answers": answers  # 보기 목록 저장
            }
            
            # 딕셔너리에 저장 (중복 ID가 있으면 덮어쓰기)
            codebook_dict[unique_id] = codebook_obj
        
        print(f"  [Stage 1] 코드북 파싱 완료. {len(codebook_dict)}개의 '실제 질문' 항목 감지.")
        
        # --- DB에 삽입 ---
        data_to_insert = [] # DB에 일괄 삽입(batch insert)할 (ID, JSON) 튜플 리스트
        for unique_id, codebook_obj in codebook_dict.items():
            json_data_string = json.dumps(codebook_obj, ensure_ascii=False) # 한글 인코딩 유지
            data_to_insert.append((unique_id, json_data_string))
            
        if data_to_insert: 
            cur = conn.cursor()
            try:
                # 'ON CONFLICT (codebook_id) DO UPDATE ...':
                # codebook_id(PK)가 이미 존재하면(welcome_2nd에서 삽입됨) 덮어쓰고,
                # 없으면 새로 삽입합니다. (멱등성 보장)
                insert_query = f"""
                INSERT INTO {CODEBOOKS_TABLE} (codebook_id, codebook_data)
                VALUES %s
                ON CONFLICT (codebook_id) DO UPDATE SET
                    codebook_data = EXCLUDED.codebook_data;
                """
                execute_values(cur, insert_query, data_to_insert)
                conn.commit() 
            except Exception as e:
                print(f"  XXX [Stage 1] 코드북 DB 삽입 중 오류 발생: {e}")
                conn.rollback()
            finally:
                cur.close()
        return True

    except Exception as e:
        print(f"  XXX [Stage 1] 코드북 시트 처리 중 오류 발생: {e}")
        return False

# --- 8. Stage 2: qpoll 패널 데이터 ETL (Pass 2) ---
def process_data_etl(conn, file_path, prefix):
    """XLSX 파일의 *첫 번째 시트(header=1)*를 파싱하여 respondents, metadata, answers로 분리 삽입합니다."""
    print(f"  [Stage 2] '{file_path}'의 패널 데이터(Sheet 1, Header 2번째줄) 처리 시작 (Prefix: {prefix})...")
    
    respondents_to_insert = set() 
    metadata_to_insert_dict = {} # (mb_sn: (데이터 튜플)) 형식, 중복 ID 덮어쓰기용
    answers_to_insert = []
    
    try:
        # --- [qpoll 핵심 로직] 2-헤더(2-line header) 파싱 ---
        
        # 1. 엑셀 파일의 *첫 번째 줄*(질문 제목)을 읽어와서 리스트로 만듭니다. (nrows=1)
        df_titles_row = pd.read_excel(file_path, sheet_name=0, engine='openpyxl', header=None, nrows=1)
        title_values = df_titles_row.iloc[0].values.tolist()

        # [중요] "Forward Fill" 로직: Excel의 병합된 셀(NaN)을 바로 앞의 유효한 제목으로 채웁니다.
        # (예: ['Q1', NaN, NaN, 'Q2', NaN] -> ['Q1', 'Q1', 'Q1', 'Q2', 'Q2'])
        last_title = ''
        title_columns = [] # (예: ['ID', '메타', '메타', 'Q1', 'Q1', 'Q2', ...])
        for val in title_values:
            # 비어있지 않고(notna), 'Unnamed'가 아닌 유효한 제목을 찾으면 last_title 갱신
            if pd.notna(val) and not str(val).startswith('Unnamed'):
                last_title = str(val).strip().replace('\n', ' ')
            # 현재 셀에 유효한 값이 있든 없든, 마지막으로 유효했던 제목(last_title)을 채워넣음
            title_columns.append(last_title)
        
        # 2. 엑셀 파일의 *두 번째 줄*(헤더 1)을 읽어와서 실제 데이터프레임으로 사용합니다.
        # (이 줄에는 'mb_sn', '문항1', '문항2' 등이 있습니다)
        df_panel = pd.read_excel(file_path, sheet_name=0, engine='openpyxl', header=1)
        panel_columns = [str(col).strip() for col in df_panel.columns]
        df_panel.columns = panel_columns # 공백 제거된 컬럼명으로 다시 설정

        # 3. 1번 리스트(제목)와 2번 리스트(컬럼명)를 zip으로 묶어 매핑 딕셔너리 생성
        # (예: {'문항1': '체력 관리', '문항2': '이용 서비스'})
        question_id_map = {
            panel_col: title_col 
            for panel_col, title_col in zip(panel_columns, title_columns)
            if panel_col not in ID_CANDIDATES and panel_col not in METADATA_COLUMNS and panel_col not in COLUMNS_TO_IGNORE
        }
        
        # --- [qpoll 핵심 로직 완료] ---

        header = panel_columns # 실제 헤더는 두 번째 줄(df_panel)의 컬럼을 사용

        # ID_CANDIDATES 목록을 순회하며 실제 파일에서 사용된 '고유번호' 컬럼명을 찾음
        mb_sn_col_name = None
        for candidate in ID_CANDIDATES:
            if candidate in header:
                mb_sn_col_name = candidate
                break
                
        if mb_sn_col_name is None: # ID 컬럼을 찾지 못하면 처리 중단
            print(f"  XXX [Stage 2] 오류: ID 컬럼({', '.join(ID_CANDIDATES)})이 없습니다. 건너뜁니다.")
            return False
        
        print(f"  [Stage 2] ID 컬럼 '{mb_sn_col_name}'을(를) mb_sn 기준으로 사용합니다.")

        # --- 데이터 변환 (Unpivot 및 콤마 분리) ---
        print("  [Stage 2] 데이터 변환(메타데이터 분리, Unpivot, 콤마 분리) 시작...")
        
        # Pandas DataFrame을 한 줄(row)씩 순회
        for row in df_panel.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리로 변환 (컬럼명: 값)
            mb_sn = str(row_dict.get(mb_sn_col_name, '')).strip() # 고유번호 추출
            
            if not mb_sn: continue # 고유번호가 없는 행은 무시
            
            # (1) respondents 테이블 데이터 추출: set에 추가 (자동으로 중복 제거됨)
            respondents_to_insert.add((mb_sn,)) 

            # (2) metadata 테이블 데이터 추출
            # qpoll의 '구분' 컬럼(통신사)을 mobile_carrier 변수에 저장
            mobile_carrier = str(row_dict.get('구분', '') or '').strip() 
            
            # '성별' 컬럼('남'/'여')을 '남성'/'여성'으로 변환
            gender_raw = str(row_dict.get('성별', '') or '').strip()
            gender = map_gender(gender_raw)
            
            # qpoll의 '나이'는 '39', '40' 등이므로, 변환 없이 원본 그대로 사용
            age = str(row_dict.get('나이', '') or '').strip()
            
            # qpoll의 '지역'은 '서울', '경기' 등이므로, 변환 없이 원본 그대로 사용
            region = str(row_dict.get('지역', '') or '').strip()
            
            # dict에 (mb_sn, mobile_carrier, ...) 형태로 저장 (중복 ID는 덮어쓰기)
            metadata_to_insert_dict[mb_sn] = (mb_sn, mobile_carrier, gender, age, region)

            # (3) answers 테이블 데이터 추출 (Unpivot 과정)
            for question_id, raw_answer_value in row_dict.items():
                
                # 이 컬럼이 ID, 메타데이터, 무시 목록에 포함되거나, 값이 비어있으면 건너뜀
                if (question_id in ID_CANDIDATES or 
                    question_id in METADATA_COLUMNS or 
                    question_id in COLUMNS_TO_IGNORE or
                    pd.isna(raw_answer_value)): 
                    continue
                
                # '문항1'을 '체력 관리' (실제 질문 제목)로 변환
                real_question_id = question_id_map.get(question_id)
                
                if not real_question_id: # 매핑에 없는 질문(예: '문항1_기타')은 무시
                    continue
                    
                # codebooks 테이블과 일치하는 unique_id 생성 (예: 'qp250106_체력 관리')
                unique_question_id = f"{prefix}{real_question_id}"
                answer_string = str(raw_answer_value).strip() 
                if not answer_string: continue # 빈 값 무시

                # 콤마(,)로 구분된 다중 응답 처리 (예: "1, 3, 4")
                split_values = [val.strip() for val in answer_string.split(',') if val.strip()]

                for final_value in split_values:
                    answers_to_insert.append((mb_sn, unique_question_id, final_value))

        # 딕셔너리(중복 제거됨)의 값들만 리스트로 변환
        metadata_to_insert_list = list(metadata_to_insert_dict.values())

        print(f"  [Stage 2] 데이터 변환 완료. {len(respondents_to_insert)}명, {len(metadata_to_insert_list)}개 메타데이터, {len(answers_to_insert)}개 답변 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # (1) Respondents 삽입
            if respondents_to_insert:
                # 'ON CONFLICT (mb_sn) DO NOTHING':
                #   mb_sn이 이미 (welcome_1st 등에서) 존재하면 무시 (Append-Only)
                respondents_query = f"""
                INSERT INTO {RESPONDENTS_TABLE} (mb_sn) 
                VALUES %s 
                ON CONFLICT (mb_sn) DO NOTHING; 
                """
                execute_values(cur, respondents_query, list(respondents_to_insert))
            
            # (2) Metadata 삽입/업데이트
            if metadata_to_insert_list:
                # [중요] COALESCE 로직:
                # welcome_1st에서 'age'를 삽입했고, qpoll의 'age'가 NULL(빈 값)이면,
                # COALESCE(welcome_age, qpoll_age_NULL) -> welcome_age (기존 값 유지)
                #
                # welcome_1st의 mobile_carrier가 NULL이었고, qpoll이 'SKT'를 삽입하면,
                # COALESCE(NULL, 'SKT') -> 'SKT' (새 값으로 갱신)
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
            
            # (3) Answers 삽입 (멱등성 보장)
            respondent_ids_in_this_file = list(respondents_to_insert) 
            if respondent_ids_in_this_file:
                respondent_id_list = [r[0] for r in respondent_ids_in_this_file]
                
                # [중요] 멱등성: 이 스크립트를 여러 번 실행해도 데이터가 중복되지 않도록,
                # 현재 qpoll 파일의 prefix(예: 'qp250106_')를 가진 기존 답변들을 먼저 삭제합니다.
                # (welcome_2nd('w2_') 데이터는 삭제되지 않습니다.)
                cur.execute(
                    f"DELETE FROM {ANSWERS_TABLE} WHERE mb_sn = ANY(%s) AND question_id LIKE %s;",
                    (respondent_id_list, f"{prefix}%") 
                )

            # Answers 대량 삽입
            if answers_to_insert:
                answers_query = f"INSERT INTO {ANSWERS_TABLE} (mb_sn, question_id, answer_value) VALUES %s;"
                execute_values(cur, answers_query, answers_to_insert)

            conn.commit() # (1), (2), (3)의 모든 DB 작업을 최종 반영
            print(f"  [Stage 2] 패널 데이터가 마스터 DB에 성공적으로 저장되었습니다.")
            return True
            
        except Exception as e:
            print(f"  XXX [Stage 2] 패널 데이터 DB 삽입 중 오류 발생: {e}")
            conn.rollback() 
            return False
        finally:
            cur.close()

    except Exception as e:
        print(f"  XXX [Stage 2] 패널 데이터 시트 처리 중 오류 발생: {e}")
        return False


# --- 9. 메인 실행 파이프라인 ---
def main():
    db_conn = connect_to_db() # 1. DB 연결
    if db_conn:
        try:
            # 2. DB 스키마(테이블) 설정 (IF NOT EXISTS)
            if not setup_master_tables(db_conn):
                print("오류: 마스터 테이블 생성에 실패하여 ETL을 중단합니다.")
                db_conn.close()
                return 
            
            print(f">>> [Phase 3] 입력 폴더 '{INPUT_FOLDER}' 스캔 시작...")
            try:
                # 3. INPUT_FOLDER의 모든 파일을 스캔
                all_files = os.listdir(INPUT_FOLDER)
                
                # [중요] 스캔된 파일 중에서...
                files_to_process = [
                    f for f in all_files 
                    if f.startswith('qpoll_join_')  # 'qpoll_join_'으로 시작하고
                    and f.endswith('.xlsx')        # '.xlsx'로 끝나고
                    and not f.startswith('~')      # 임시 파일('~')이 아니고
                    and f not in FILES_TO_IGNORE # 'Welcome' 등 무시 목록에 없는 파일만
                ]
                
                # 무시 목록에 있는 파일들을 로그로 출력
                ignored_files = [f for f in all_files if f in FILES_TO_IGNORE]
                for f in ignored_files:
                    print(f"  [Info] 건너뛰는 파일: '{f}'")

            except FileNotFoundError:
                print(f"XXX 오류: '{INPUT_FOLDER}' 폴더를 찾을 수 없습니다.")
                files_to_process = []

            if not files_to_process:
                print(">>> [Phase 4] 처리할 'qpoll_join_' .xlsx 파일이 없습니다.")
            else:
                print(f">>> [Phase 4] qpoll 파일 ({len(files_to_process)}개) 처리 시작...")

            # 4. [qpoll 핵심] 2-Pass Loop (2중 루프):
            # qpoll 엑셀 파일은 (1)코드북과 (2)데이터가 한 파일에 같이 있으므로,
            # 모든 파일의 (1)코드북을 먼저 다 처리하고,
            # 다시 모든 파일의 (2)데이터를 처리합니다.
            
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
            db_conn.rollback() 
        finally:
            # 5. 스크립트가 성공하든 실패하든 DB 연결 종료
            db_conn.close() 
            print(">>> [Phase 6] PostgreSQL DB 연결 종료.")

# --- 10. 스크립트 실행 ---
# 'python qpoll_etl_script.py'로 직접 실행되었을 때만 main() 함수를 호출
if __name__ == '__main__':
    main()

