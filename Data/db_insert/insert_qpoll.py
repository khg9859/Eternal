# -*- coding: utf-8 -*-
"""
Qpoll ETL 스크립트 (Append-Only, INT Age, NaN Fix Version)

[스크립트의 목적]
이 스크립트는 'qpoll_join_*.xlsx' (qpoll 설문) 엑셀 파일들을 처리합니다.
이 파일들은 'welcome' 데이터와 형식이 완전히 다릅니다.

1. 'Sheet 2' (코드북)는 '수평' 형식 (질문이 행, 보기가 열)입니다.
2. 'Sheet 1' (데이터)는 '2줄 헤더' (첫 줄은 질문 제목, 둘째 줄은 '문항1' 같은 ID)입니다.

[주요 기능]
1. .env 파일을 통해 DB 접속 정보를 안전하게 로드합니다.
2. 4개 마스터 테이블('respondents', 'metadata', 'codebooks', 'answers')이
   'birth_year INT', 'age INT' 스키마로 (없으면) 생성되도록 합니다. (IF NOT EXISTS)
3. 'Sheet 2'를 파싱하여 'codebooks' 테이블에 질문/보기 정보를 JSONB로 저장합니다.
4. 'Sheet 1'의 '2줄 헤더'를 파싱하고 'Forward Fill'로 병합된 셀을 처리하여,
   '문항1'을 '체력 관리' 같은 실제 질문 ID로 매핑합니다.
   - [수정] '문항1_ETC' 같은 기타(ETC) 컬럼이 '문항1'과 동일한 ID로 매핑되는 오류를 수정합니다.
5. 'Sheet 1'의 데이터를 'respondents', 'metadata', 'answers' 3개 테이블로 분리하여 저장합니다.
   - [수정] pd.isna() 및 'nan' 문자열 검사를 통해 빈 ID가 DB에 삽입되는 오류를 수정합니다.
   - [수정] 정규식(Regex)을 사용해 '나이' 컬럼(예: '39.0', '(만 39세)')에서 숫자만 추출하여 변환합니다.
6. 'qp_' 접두사를 사용하여 다른 데이터(w2_)와 ID가 충돌하지 않도록 합니다.

"""

# --- 1. 라이브러리 임포트 ---
# 파이썬에 기본 내장되지 않은 외부 기능(도구)들을 가져옵니다.

# PostgreSQL 데이터베이스에 연결하고 SQL 명령을 실행할 수 있게 해주는 메인 라이브러리
import psycopg2 
# psycopg2의 확장 기능으로, (mb_sn, 'SKT', ...) 같은 튜플 리스트를
# 한 번의 SQL 명령으로 매우 빠르게 DB에 삽입할 수 있게 도와줍니다.
from psycopg2.extras import execute_values 
# 엑셀(.xlsx)이나 CSV 파일을 "데이터 표"처럼 쉽게 읽고 다룰 수 있게 해주는
# 데이터 분석의 필수 라이브러리입니다. (엑셀 = DataFrame)
import pandas as pd 
# 파이썬의 딕셔너리(dict)나 리스트(list)를 
# '[{"key": "value"}]' 같은 JSON 문자열로 변환할 때 사용합니다. (한글 인코딩 처리에 유용)
import json 
# 'os'는 'Operating System'(운영체제)의 약자로, 
# 'D:/capstone/...' 같은 파일 경로를 다루거나, 'DB_PASSWORD' 같은 환경 변수를 읽을 때 사용합니다.
import os 
# '.env' 파일에 적어둔 DB 비밀번호 같은 민감한 정보를
# os.getenv()로 읽을 수 있도록 '환경 변수'로 로드해주는 라이브러리입니다.
from dotenv import load_dotenv, find_dotenv 
# '나이'로부터 '출생년도'를 역산하기 위해 '현재 년도'를 알아야 하므로 import합니다.
from datetime import datetime 
# [신규] 'age' 컬럼에서 숫자만 추출하기 위해 정규식(Regular Expression) 라이브러리 임포트
import re 

# [안내] 이 스크립트는 pandas가 XLSX 파일을 읽을 수 있도록 'openpyxl' 라이브러리가 필요합니다.
# (pip install psycopg2-binary pandas openpyxl python-dotenv)

# --- 2. .env 파일 로드 ---
# find_dotenv(): 현재 폴더나 상위 폴더에서 '.env' 파일의 위치를 자동으로 찾습니다.
# load_dotenv(...): 찾은 '.env' 파일 안의 'DB_HOST=localhost' 같은 내용들을
# '환경 변수'로 로드하여, os.getenv('DB_HOST')로 읽을 수 있게 준비시킵니다.
load_dotenv(find_dotenv())

# --- 3. 설정 (Configuration) ---
# 스크립트 전체에서 사용할 고정 값(설정)들을 변수로 정의합니다.

# os.getenv('KEY', 'DEFAULT') 형식:
# 1. '환경 변수'에서 'KEY' (예: 'DB_HOST')를 찾습니다.
# 2. .env 파일에 'KEY'가 없으면(None) 'DEFAULT' (예: 'localhost') 값을 대신 사용합니다.
DB_HOST = os.getenv('DB_HOST','localhost') 
DB_PORT = os.getenv('DB_PORT','5432')
DB_NAME = os.getenv('DB_NAME') # (필수 값이므로 기본값 없음)
DB_USER = os.getenv('DB_USER','postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD') # (필수 값이므로 기본값 없음)

# .env 파일에서 'INPUT_PATH' (데이터 폴더 경로)를 읽어옵니다.
INPUT_FOLDER = os.getenv('INPUT_PATH')

# [방어 코드] 스크립트 실행에 필수적인 값들이 .env에 없는 경우,
# (예: DB_NAME이 None일 경우) 명확한 오류 메시지를 주고 즉시 종료합니다.
if not all([DB_NAME, DB_PASSWORD, INPUT_FOLDER]):
    print("XXX [오류] .env 파일에 DB_NAME, DB_PASSWORD, INPUT_PATH 중 하나 이상이 설정되지 않았습니다.")
    print("XXX .env 파일이 스크립트와 같은 경로에 있는지, 키 이름이 맞는지 확인하세요.")
    exit() # 스크립트 강제 종료

# --- 테이블 및 컬럼 이름 정의 ---
# 테이블 이름을 변수로 빼두면, 나중에 'metadata'를 'user_profiles'로 바꾸고 싶을 때
# 이 변수 하나만 수정하면 모든 SQL 쿼리가 자동으로 변경되어 편리합니다.
RESPONDENTS_TABLE = 'respondents' 
ANSWERS_TABLE = 'answers' 
CODEBOOKS_TABLE = 'codebooks' 
METADATA_TABLE = 'metadata' 

# qpoll 엑셀(Sheet 1)에서 '고유번호'로 사용될 컬럼 이름 후보 목록
# (파일마다 'mb_sn', '고유번호' 등 이름이 다를 수 있으므로 리스트로 관리)
ID_CANDIDATES = ['mb_sn', '고유번호', '패널ID', 'id']
# 'metadata' 테이블에 직접 저장할 (answers 테이블에 넣지 않을) 메타데이터 컬럼 목록
# (Sheet 1의 '성별', '나이' 등은 "답변"이 아니라 "프로필"이므로 분리)
METADATA_COLUMNS = ['구분', '성별', '나이', '지역']
# ETL 과정에서 무시할 컬럼 목록 (예: '설문일시'는 분석에 불필요)
COLUMNS_TO_IGNORE = ['설문일시']
# 이 스크립트(qpoll)가 실수로 Welcome 파일들을 처리하지 않도록, 무시할 파일 목록 정의
FILES_TO_IGNORE = [
    'Welcome_1st.xlsx', 'welcome_2nd.xlsx', 
    'Welcome_1st.csv', 'welcome_1st_codebook.csv', 
    'wel_1st.ex.csv', 'wel_2ndex.csv', 'welcome_2nd_codebook.csv'
]


# --- 4. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
    print(">>> [Phase 1] PostgreSQL DB 연결 시도...")
    try:
        # 3번 설정(Config)에서 .env로부터 읽어온 변수들을 사용해 DB 연결 시도
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        print(">>> [Phase 1] PostgreSQL DB 연결 성공.")
        return conn # 연결 성공 시, 연결 객체(conn)를 반환
    except psycopg2.OperationalError as e:
        # (예: 비밀번호 틀림, DB 이름 오타, PostgreSQL 서버 꺼져있음 등)
        print(f"XXX [Phase 1] DB 연결 실패: {e}")
        return None # 연결 실패 시 None 반환

# --- 5. 마스터 테이블 확인/생성 함수 ---
def setup_master_tables(conn):
    """
    [수정] 'metadata' 테이블이 'birth_year INT', 'age INT' 스키마로 (없으면) 생성되도록 합니다.
    (Append-Only)
    """
    
    # 4개 테이블의 'CREATE TABLE IF NOT EXISTS' 쿼리 목록
    # 'IF NOT EXISTS': 테이블이 이미 존재하면 이 쿼리를 조용히 무시합니다.
    # (데이터 보존을 위해 DROP하지 않음)
    queries = [
        # 1. respondents: 사용자의 고유 ID(mb_sn)와 P-벡터(profile_vector) 저장
        f"""CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (
            mb_sn VARCHAR(255) PRIMARY KEY, 
            profile_vector TEXT DEFAULT NULL
        );""",
        
        # 2. metadata [중요]
        # 'welcome_1st'에서 변경한 'birth_year INT', 'age INT' 스키마를
        # 이 스크립트에서도 동일하게 사용해야 합니다.
        f"""CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
            metadata_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            mobile_carrier VARCHAR(100) DEFAULT NULL,
            gender VARCHAR(10) DEFAULT NULL,
            birth_year INT DEFAULT NULL, 
            age INT DEFAULT NULL, 
            region VARCHAR(100) DEFAULT NULL
        );""",

        # 3. codebooks: 질문 ID(pk)와 질문/보기 내용(JSON) 저장
        f"CREATE TABLE IF NOT EXISTS {CODEBOOKS_TABLE} (codebook_id VARCHAR(255) PRIMARY KEY, codebook_data JSONB);",
        
        # 4. answers: 실제 답변 내역 (가장 용량이 큰 테이블)
        f"""CREATE TABLE IF NOT EXISTS {ANSWERS_TABLE} (
            answer_id SERIAL PRIMARY KEY,
            mb_sn VARCHAR(255) REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
            question_id VARCHAR(255), 
            answer_value TEXT
        );""",
        
        # 5. 인덱스 생성 (IF NOT EXISTS)
        # RAG 검색 시 'answers' 테이블에서 특정 사용자(mb_sn)의 답변을 빠르게 찾기 위함
        f"CREATE INDEX IF NOT EXISTS idx_answers_respondent ON {ANSWERS_TABLE} (mb_sn);",
        # RAG 검색 시 'answers' 테이블에서 특정 질문(question_id)에 대한 답변을 빠르게 찾기 위함
        f"CREATE INDEX IF NOT EXISTS idx_answers_question ON {ANSWERS_TABLE} (question_id);"
    ]
    
    # DB 연결(conn)로부터 '커서'(SQL 실행기)를 생성
    cur = conn.cursor()
    try:
        print(">>> [Phase 2] 마스터 테이블 4개 (respondents, metadata, codebooks, answers) 셋업 확인...")
        
        # 위에서 정의한 모든 CREATE 쿼리를 실행 (IF NOT EXISTS로 안전하게)
        for query in queries:
            cur.execute(query)
            
        # [중요] 스키마가 변경되었음을 로그로 알려줌
        # 만약 DB에 'age VARCHAR(50)'을 가진 옛날 metadata 테이블이 있다면,
        # 'CREATE TABLE IF NOT EXISTS'는 스키마가 달라도 테이블이 존재한다고 판단하여
        # 이 쿼리를 무시하고 넘어갑니다.
        # 이 경우, DB에서 metadata 테이블을 수동으로 DROP해야 스키마가 갱신됩니다.
        print("  [Info] (참고) metadata 테이블 스키마가 'birth_year INT, age INT'로 변경되었습니다.")
        print("  [Info] 만약 기존 'age VARCHAR' 컬럼이 존재한다면, DB에서 수동으로 'DROP TABLE metadata CASCADE;' 실행 후 이 스크립트를 재실행하세요.")
        
        # 모든 쿼리가 성공하면, 변경 사항을 DB에 최종 반영(커밋)
        conn.commit() 
        return True # 성공 반환
    except Exception as e:
        # 쿼리 실행 중 오류 발생 시 (예: 문법 오류)
        print(f"XXX [Phase 2] 테이블 설정 중 오류 발생: {e}")
        conn.rollback() # 모든 변경 사항을 되돌림(롤백)
        return False # 실패 반환
    finally:
        # 성공하든 실패하든, 커서를 항상 닫아서 DB 자원 반납
        cur.close()

# --- 6. 헬퍼 함수 (데이터 변환용) ---

def clean_cell(val):
    """
    [신규] pandas/numpy의 NaN 및 'nan' 문자열을 안전하게 처리하여
    DB에 'nan' 텍스트가 삽입되는 것을 방지합니다.
    """
    # 1. pandas의 NaN (Not a Number)인지 확인
    if pd.isna(val):
        return '' # NaN이면 빈 문자열 반환
    # 2. 문자열로 변환하고 양쪽 공백 제거
    s = str(val).strip()
    # 3. 변환된 문자열이 'nan' (소문자)인지 확인
    if s.lower() == 'nan':
        return '' # 'nan' 문자열도 빈 문자열로 반환
    # 4. 유효한 텍스트만 반환
    return s

def map_gender(gender_raw):
    """ [qpoll 전용] '남'/'여'를 '남성'/'여성'으로 변환합니다. """
    # 'gender_raw'는 이미 clean_cell을 거쳐 '' 또는 '남'/'여'가 됨
    if gender_raw == '남':
        return '남성'
    elif gender_raw == '여':
        return '여성'
    return gender_raw # '남성'/'여성'이거나 ''이면 원본 반환

def parse_qpoll_age_info(age_raw_str):
    """
    Qpoll 전용 간소화 버전.
    예시 입력: "1971년 03월 07일 (만 54 세)"
    반환: (1971, 54)
    """
    if not age_raw_str:
        return (None, None)
    s = str(age_raw_str).strip()

    # 1️⃣ 생년 추출
    birth_year_match = re.search(r'(19|20)\d{2}', s)
    birth_year = int(birth_year_match.group(0)) if birth_year_match else None

    # 2️⃣ (만 NN 세), (NN세), (만NN세) 등 변형 대응
    age_match = re.search(r'만?\s*(\d{1,3})\s*세', s)
    age = int(age_match.group(1)) if age_match else None

    return (birth_year, age)

# --- 7. Stage 1: qpoll 코드북 ETL (Pass 1) ---
def process_codebook_etl(conn, file_path, prefix):
    """qpoll의 '수평' 형식 코드북(Sheet 2, header=0)을 파싱하여 DB에 삽입합니다."""
    print(f"  [Stage 1] '{file_path}'의 qpoll 코드북(Sheet 2) 처리 시작 (Prefix: {prefix})...")
    
    try:
        # "두 번째 시트"(index 1)를 읽음, "첫 번째 줄"(header=0)을 헤더로 사용
        df_codebook = pd.read_excel(file_path, sheet_name=1, engine='openpyxl', header=0)
        
        # [중요] 중복된 질문 ID(q_title)를 덮어쓰기 위해 딕셔너리 사용
        # (리스트는 [A, B, A]가 가능하지만, 딕셔너리는 {'A': B}로 중복이 안 됨)
        codebook_dict = {} 

        # 시트의 모든 행 (각 행 = 질문 1개)을 순회
        for row in df_codebook.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리로 변환 (예: {'설문제목': '...'})
            
            # '설문제목' 컬럼 값을 질문 제목이자 ID로 사용
            q_title = str(row_dict.get('설문제목', '')).strip()
            if not q_title:
                continue # 질문 제목이 없으면 무시
                
            # '설문제목'이 '성별', '나이' 등 메타데이터 컬럼명이면 무시
            if q_title in METADATA_COLUMNS or q_title in ID_CANDIDATES:
                continue

            # \n (개행 문자)가 ID에 포함되는 것을 방지 (DB ID로 부적합)
            cleaned_q_title = q_title.replace('\n', ' ')
            # codebooks 테이블의 PK (예: 'qp250106_체력 관리')
            unique_id = f"{prefix}{cleaned_q_title}"
            answers = [] # 이 질문의 보기 목록 (예: [{'qi_val': '1', 'qi_title': '헬스'}])
            
            # 이 시트(Sheet 2)는 '보기1', '보기2', ... '보기10' 열(column)을 가짐
            max_options = 10 
            for i in range(1, max_options + 1):
                qi_title_key = f'보기{i}' # '보기1', '보기2', ...
                qi_title = str(row_dict.get(qi_title_key, '')).strip() # '보기1'의 값 (예: '헬스')
                qi_val = str(i) # 보기 값 (예: '1')
                
                # '보기n' 컬럼에 유효한 텍스트가 있을 경우에만
                if qi_title and pd.notna(row_dict.get(qi_title_key)):
                    answers.append({"qi_val": qi_val, "qi_title": qi_title})

            # DB의 codebook_data (JSONB) 컬럼에 저장할 JSON 객체 생성
            codebook_obj = {
                "codebook_id": unique_id, # (검색용 ID)
                "q_title": q_title, # (임베딩 및 표기용) 원본 질문 제목
                "answers": answers  # (RAG에서 보기 매핑용) 보기 목록
            }
            
            # 딕셔너리에 저장 (만약 unique_id가 중복되면, 새 값으로 덮어써짐)
            codebook_dict[unique_id] = codebook_obj
        
        print(f"  [Stage 1] 코드북 파싱 완료. {len(codebook_dict)}개의 '실제 질문' 항목 감지.")
        
        # --- DB에 삽입 ---
        data_to_insert = [] # DB에 일괄 삽입(batch insert)할 (ID, JSON) 튜플 리스트
        for unique_id, codebook_obj in codebook_dict.items():
            # JSON 객체를 한글(utf-8)이 깨지지 않는 문자열로 변환
            json_data_string = json.dumps(codebook_obj, ensure_ascii=False) 
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
                # execute_values: data_to_insert 리스트를 한 번의 쿼리로 DB에 전송
                execute_values(cur, insert_query, data_to_insert)
                conn.commit() # DB에 최종 반영
            except Exception as e:
                print(f"  XXX [Stage 1] 코드북 DB 삽입 중 오류 발생: {e}")
                conn.rollback() # 오류 시 롤백
            finally:
                cur.close() # 커서 닫기
        return True

    except Exception as e:
        print(f"  XXX [Stage 1] 코드북 시트 처리 중 오류 발생: {e}")
        return False

# --- 8. Stage 2: qpoll 패널 데이터 ETL (Pass 2) ---
def process_data_etl(conn, file_path, prefix):
    """[수정] NaN/'nan' 문자열 및 'age' 컬럼의 자료 변환 문제를 해결한 ETL 함수"""
    print(f"  [Stage 2] '{file_path}'의 패널 데이터(Sheet 1, Header 2번째줄) 처리 시작 (Prefix: {prefix})...")
    
    respondents_to_insert = set() # (중복 ID 제거용)
    metadata_to_insert_dict = {} # (중복 ID 덮어쓰기용)
    answers_to_insert = [] # (모든 답변 저장용)
    
    try:
        # --- [qpoll 핵심 로직] 2-헤더(2-line header) 파싱 ---
        
        # 1. 엑셀 파일의 *첫 번째 줄*(질문 제목)을 읽어와서 리스트로 만듭니다. (nrows=1)
        # (예: ['mb_sn', '구분', '성별', '나이', '지역', '여러분은 평소...', NaN, NaN, '귀하는 현재...'])
        df_titles_row = pd.read_excel(file_path, sheet_name=0, engine='openpyxl', header=None, nrows=1)
        title_values = df_titles_row.iloc[0].values.tolist()

        # [중요] "Forward Fill" 로직: Excel의 병합된 셀(NaN)을 바로 앞의 유효한 제목으로 채웁니다.
        # (예: ['Q1', NaN, NaN, 'Q2', NaN] -> ['Q1', 'Q1', 'Q1', 'Q2', 'Q2'])
        last_title = ''
        title_columns = [] # (예: ['mb_sn', '구분', '성별', '나이', '지역', '여러분은 평소...', '여러분은 평소...', ...])
        for val in title_values:
            # 비어있지 않고(notna), 'Unnamed'가 아닌 유효한 제목을 찾으면 last_title 갱신
            if pd.notna(val) and not str(val).startswith('Unnamed'):
                last_title = str(val).strip().replace('\n', ' ')
            # 현재 셀에 유효한 값이 있든 없든, 마지막으로 유효했던 제목(last_title)을 채워넣음
            title_columns.append(last_title)
        
        # 2. 엑셀 파일의 *두 번째 줄*(헤더 1)을 읽어와서 실제 데이터프레임으로 사용합니다.
        # (이 줄에는 'mb_sn', '구분', '성별', '나이', '지역', '문항1', '문항2', '문항3', '문항4' 등이 있습니다)
        df_panel = pd.read_excel(file_path, sheet_name=0, engine='openpyxl', header=1)
        panel_columns = [str(col).strip() for col in df_panel.columns] # ['mb_sn', '구분', ..., '문항1', '문항2', ...]
        df_panel.columns = panel_columns # 공백 제거된 컬럼명으로 다시 설정

        # 3. 1번 리스트(제목)와 2번 리스트(컬럼명)를 zip으로 묶어 매핑 딕셔너리 생성
        # (예: {'문항1': '여러분은 평소...', '문항2': '여러분은 평소...', '문항4': '귀하는 현재...'})
        question_id_map = {
            panel_col: title_col # (key: '문항1', value: '여러분은 평소...')
            for panel_col, title_col in zip(panel_columns, title_columns)
            # ID, 메타데이터, 무시 컬럼이 아닌 "진짜 질문" 컬럼만 맵에 추가
            if (panel_col not in ID_CANDIDATES and 
                panel_col not in METADATA_COLUMNS and 
                panel_col not in COLUMNS_TO_IGNORE and
                not panel_col.endswith('_ETC')) # [수정] '_ETC' (기타) 컬럼은 매핑에서 제외
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
        
        dropped_rows_count = 0 # [신규] NaN ID로 인해 건너뛴 행 카운트

        # Pandas DataFrame을 한 줄(row)씩 순회
        for row in df_panel.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리로 변환 (컬럼명: 값)
            
            # [수정] 'nan' 문자열 삽입 버그 수정
            # 1. 원본 값(NaN일 수 있음)을 가져옵니다.
            raw_mb_sn = row_dict.get(mb_sn_col_name)
            # 2. clean_cell 함수로 NaN, 'nan', 공백을 ''(빈 문자열)로 정제합니다.
            mb_sn = clean_cell(raw_mb_sn)
            
            # 3. 정제된 ID가 빈 문자열이면 (즉, 원본이 NaN 또는 빈 값이었으면) 이 행 전체를 건너뜁니다.
            if not mb_sn: 
                dropped_rows_count += 1
                continue 
            
            # (1) respondents 테이블 데이터 추출: set에 (mb_sn,) 튜플 추가 (자동 중복 제거)
            respondents_to_insert.add((mb_sn,)) 

            # (2) metadata 테이블 데이터 추출
            # [수정] 모든 메타데이터 추출에 clean_cell 적용
            mobile_carrier = clean_cell(row_dict.get('구분'))
            
            gender_raw = clean_cell(row_dict.get('성별'))
            gender = map_gender(gender_raw) # '남'/'여' -> '남성'/'여성'
            
            # [수정] age 변환 로직 (Regex로 숫자 추출)
            # 1. '나이' 컬럼에서 정제된 문자열(예: '(만 39세)' 또는 '39.0')을 가져옴
            age_raw_cleaned = clean_cell(row_dict.get('나이')) 
            
            age_digits_str = age_raw_cleaned # 기본값
            
            # 2. 정규식(Regex)을 사용해 텍스트에서 첫 번째 숫자 그룹(예: 39)을 추출
            match = re.search(r'(\d{1,4})', age_raw_cleaned)
            if match:
                age_digits_str = match.group(1) # '39'
            
            # 3. 정제된 숫자 문자열('39')을 헬퍼 함수로 전달
            birth_year, age = parse_qpoll_age_info(age_raw_cleaned) # (1986, 39) 또는 (None, None) 반환
            
            region = clean_cell(row_dict.get('지역')) # '서울', '경기' 등
            
            # [수정] 딕셔너리에 (mb_sn, ..., birth_year, age, region) 형태로 저장
            # (파일 내에 동일 mb_sn이 있으면 마지막 값으로 덮어써짐)
            metadata_to_insert_dict[mb_sn] = (mb_sn, mobile_carrier, gender, birth_year, age, region)

            # (3) answers 테이블 데이터 추출 (Unpivot 과정)
            # 딕셔너리의 (key, value) 쌍을 순회 (key='문항1', value='1')
            for question_id, raw_answer_value in row_dict.items():
                
                # 이 컬럼이 ID, 메타데이터, 무시 목록에 포함되면 건너뜀
                if (question_id in ID_CANDIDATES or 
                    question_id in METADATA_COLUMNS or 
                    question_id in COLUMNS_TO_IGNORE): 
                    continue
                
                # '문항1'을 '여러분은 평소...' (실제 질문 제목)로 변환
                real_question_id = question_id_map.get(question_id)
                
                if not real_question_id: 
                    # 매핑에 없는 질문(예: '문항1_ETC')은 무시
                    continue
                    
                # codebooks 테이블과 일치하는 unique_id 생성 (예: 'qp250106_여러분은 평소...')
                unique_question_id = f"{prefix}{real_question_id}"
                
                # [수정] 답변 값도 clean_cell로 정제 (NaN -> '')
                answer_string = clean_cell(raw_answer_value)
                
                # 정제된 답변이 빈 문자열이면(원본이 NaN 또는 빈 값) 무시
                if not answer_string: 
                    continue 

                # 콤마(,)로 구분된 다중 응답 처리 (예: "1, 3, 4" -> ['1', '3', '4'])
                split_values = [val.strip() for val in answer_string.split(',') if val.strip()]

                # 분리된 각 값을 별개의 행으로 answers_to_insert 리스트에 추가
                for final_value in split_values:
                    answers_to_insert.append((mb_sn, unique_question_id, final_value))

        # 딕셔너리(중복 제거됨)의 값들만 리스트로 변환
        metadata_to_insert_list = list(metadata_to_insert_dict.values())

        print(f"  [Stage 2] 데이터 변환 완료. (ID 없는 {dropped_rows_count}개 행 건너뜀)")
        print(f"  [Stage 2] {len(respondents_to_insert)}명, {len(metadata_to_insert_list)}개 메타데이터, {len(answers_to_insert)}개 답변 감지.")

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
                # [수정] INSERT 및 ON CONFLICT 구문 수정 (birth_year, age)
                # [설명] COALESCE(metadata.column, EXCLUDED.column)
                # 이 로직은 '기존 DB 값 우선' 정책입니다.
                # (예: welcome_1st의 '1984'(birth_year) 값을 qpoll의 '1986'(추정치)로 덮어쓰지 않도록 방지)
                metadata_query = f"""
                INSERT INTO {METADATA_TABLE} (mb_sn, mobile_carrier, gender, birth_year, age, region) 
                VALUES %s 
                ON CONFLICT (mb_sn) DO UPDATE SET
                    mobile_carrier = COALESCE({METADATA_TABLE}.mobile_carrier, EXCLUDED.mobile_carrier),
                    gender = COALESCE({METADATA_TABLE}.gender, EXCLUDED.gender),
                    birth_year = COALESCE({METADATA_TABLE}.birth_year, EXCLUDED.birth_year),
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
            # 모든 파일의 (1)코드북을 먼저 다 처리하고 (Pass 1),
            # 다시 모든 파일의 (2)데이터를 처리합니다 (Pass 2).
            # (데이터 처리 시 코드북 매핑이 필요할 수 있으므로 코드북을 먼저 처리하는 것이 안전함)
            
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
            # main() 함수 레벨에서 예기치 못한 오류 발생 시
            print(f"XXX 메인 실행 중 오류 발생: {e}")
            db_conn.rollback() # DB 롤백
        finally:
            # 5. 스크립트가 성공하든 실패하든 DB 연결 종료
            db_conn.close() 
            print(">>> [Phase 6] PostgreSQL DB 연결 종료.")

# --- 10. 스크립트 실행 ---
# 'python qpoll_etl_script_commented.py'로 직접 실행되었을 때만 main() 함수를 호출
# (다른 스크립트에서 이 파일을 import할 때는 main()이 실행되지 않음)
if __name__ == '__main__':
    main()