# -*- coding: utf-8 -*-
"""
Welcome 1st ETL 스크립트 (Append-Only, INT Age Version)

[수정] 이 스크립트는 'metadata' 테이블의 'age' 컬럼을
'birth_year INT'와 'age INT'로 분리하여 저장합니다.

주요 기능:
1. .env 파일을 통해 DB 접속 정보를 안전하게 로드합니다.
2. 'respondents' 테이블과 [수정된] 'metadata' 테이블이 없으면 생성합니다.
3. 'Welcome_1st' 데이터의 'Q11'(출생년도)을 'birth_year'에,
   계산된 '만 나이'를 'age'에 저장합니다.
"""

# --- 1. 라이브러리 임포트 ---
import psycopg2 
from psycopg2.extras import execute_values 
import pandas as pd 
from datetime import datetime # '만 나이' 계산을 위해 현재 년도 확인용
from dotenv import load_dotenv,find_dotenv 
import os 

# --- 2. .env 파일 로드 ---
load_dotenv(find_dotenv())

# --- 3. 설정 (Configuration) ---
DB_HOST = os.getenv('DB_HOST','localhost') 
DB_PORT = os.getenv('DB_PORT','5432')
DB_NAME = os.getenv('DB_NAME') 
DB_USER = os.getenv('DB_USER','postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')
INPUT_FOLDER = os.getenv('INPUT_PATH')

# [방어 코드]
if not all([DB_NAME, DB_PASSWORD, INPUT_FOLDER]):
    print("XXX [오류] .env 파일에 DB_NAME, DB_PASSWORD, INPUT_PATH 중 하나 이상이 설정되지 않았습니다.")
    print("XXX 스크립트와 같은 경로에 .env 파일이 있는지 확인하세요.")
    exit() 

WELCOME_FILES_TO_PROCESS = [
    'welcome_1st.csv'
]

RESPONDENTS_TABLE = 'respondents' 
METADATA_TABLE = 'metadata' 
ID_CANDIDATES = ['mb_sn', '고유번호', '패널ID', 'id']

# --- 4. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
    print(">>> [Phase 1] PostgreSQL DB 연결 시도...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print(">>> [Phase 1] PostgreSQL DB 연결 성공.")
        return conn 
    except psycopg2.Error as e:
        print(f"XXX [Phase 1] DB 연결 실패: {e}")
        return None

# --- 5. 마스터 테이블 셋업 함수 ---
def setup_master_tables(conn):
    """
    [수정] metadata 테이블의 age 컬럼을 birth_year INT, age INT로 수정합니다.
    (Append-Only: IF NOT EXISTS)
    """
    
    try:
        with conn.cursor() as cur:
            
            print("  [Info] 마스터 테이블 (respondents, metadata) 확인 및 (없으면) 생성 중...")
            
            # 1. respondents 테이블 생성 (IF NOT EXISTS)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (
                    mb_sn VARCHAR(255) PRIMARY KEY,
                    profile_vector TEXT DEFAULT NULL 
                );
            """)
            
            # 2. metadata 테이블 생성 (IF NOT EXISTS)
            # [수정] age VARCHAR(50) -> birth_year INT, age INT
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
                    metadata_id SERIAL PRIMARY KEY,
                    mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
                    mobile_carrier VARCHAR(100) DEFAULT NULL,
                    gender VARCHAR(10) DEFAULT NULL,
                    birth_year INT DEFAULT NULL, 
                    age INT DEFAULT NULL, 
                    region VARCHAR(100) DEFAULT NULL
                );
            """)
            
            # [수정] 스키마 호환성 확인 (이미 age VARCHAR(50)이 존재하면 오류 방지)
            # (이 스크립트를 재실행하기 전에, DB에서 metadata 테이블을 수동으로 DROP해야 할 수도 있습니다)
            print("  [Info] (참고) metadata 테이블 스키마가 변경되었습니다. 기존 age 컬럼이 있다면 DB에서 수동 삭제가 필요할 수 있습니다.")

            conn.commit()
        print(">>> [Phase 2] 마스터 테이블 2개 (respondents, metadata) 셋업 완료.")
    
    except psycopg2.Error as e:
        conn.rollback() 
        print(f"XXX [Phase 2] 테이블 셋업 실패: {e}")
        raise 

# --- 6. 헬퍼 함수 (데이터 변환용) ---

def parse_age_info(birth_year_str):
    """ 
    [수정] '1984' 같은 출생년도 문자열을 (1984, 41) 튜플로 변환합니다.
    (birth_year_int, age_int) 반환
    """
    
    # 입력값이 4자리 숫자가 아니면 (예: 'NULL', '39', '모름') 변환하지 않고 (None, None) 반환
    if not birth_year_str or not str(birth_year_str).isdigit() or len(str(birth_year_str)) != 4:
        return (None, None) # DB에 NULL로 들어가도록 None 반환
    try:
        birth_year = int(birth_year_str)
        current_year = datetime.now().year
        # (현재 년도 - 출생 년도)로 '만 나이' 계산
        age = current_year - birth_year 
        return (birth_year, age) # (1984, 41) 튜플 반환
    except ValueError:
        return (None, None) # int 변환 중 오류 시

def map_gender(gender_raw):
    """ 'M'/'F'를 '남성'/'여성'으로 변환합니다. """
    gender_str = str(gender_raw).strip().upper() 
    if gender_str == 'M':
        return '남성'
    elif gender_str == 'F':
        return '여성'
    return gender_raw 

# --- 7. Welcome 데이터 ETL 함수 ---
def process_welcome_etl(conn, file_path):
    """[수정] Welcome 파일을 파싱하여 birth_year, age를 metadata에 삽입/업데이트합니다."""
    print(f"  [Stage 3] '{file_path}'의 Welcome 데이터 처리 시작...")
    
    respondents_to_insert = set() 
    metadata_to_insert_list = []  
    
    try:
        df_data = None 
        
        # --- 파일 확장자에 따라 다르게 읽기 ---
        if file_path.endswith('.xlsx'):
            df_data = pd.read_excel(file_path, sheet_name=0, engine='open_pyxl')
        elif file_path.endswith('.csv'):
            try:
                df_data = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                print("  [Stage 3] UTF-8 디코딩 실패. CP949로 재시도...")
                df_data = pd.read_csv(file_path, encoding='cp949')
        
        if df_data is None:
            print("XXX [Stage 3] 지원하지 않는 파일 형식입니다. (CSV 또는 XLSX만 가능)")
            return

        # --- 고유 ID 컬럼 찾기 ---
        id_column = None
        for col in ID_CANDIDATES: 
            if col in df_data.columns:
                id_column = col 
                break
        
        if id_column != 'mb_sn':
            print(f"  [Warning] DB 기본 키는 'mb_sn'이지만, CSV 파일에서 '{id_column}'을 ID로 사용합니다.")
            if 'mb_sn' in df_data.columns:
                 id_column = 'mb_sn' 
                 print(f"  [Info] 'mb_sn' 컬럼이 존재하여 기본 ID로 강제 사용합니다.")
                 
        if not id_column:
            print(f"XXX [Stage 3] 고유 ID 컬럼({', '.join(ID_CANDIDATES)})을 찾을 수 없습니다. 이 파일을 건너뜁니다.")
            return

        print(f"  [Stage 3] 고유 ID 컬럼으로 '{id_column}'을 사용합니다.")

        # --- 데이터 추출 및 변환 ---
        for row in df_data.itertuples(index=False):
            row_dict = row._asdict() 
            mb_sn = str(row_dict.get(id_column, '')).strip() 
            
            if not mb_sn: continue 
            
            # (1) respondents 테이블용 데이터
            respondents_to_insert.add((mb_sn,))
            
            # (2) metadata 테이블용 데이터 변환
            
            mobile_carrier = None 
            
            gender_raw = str(row_dict.get('Q10', '')).strip()
            gender = map_gender(gender_raw)
            
            # [수정] age 변환 로직 (birth_year, age 분리)
            age_raw = str(row_dict.get('Q11', '')).strip() 
            birth_year, age = parse_age_info(age_raw) # (1984, 41) 또는 (None, None) 반환
            
            q2_1_clean = str(row_dict.get('Q12_1', '')).strip()
            q2_2_clean = str(row_dict.get('Q12_2', '')).strip()
            region = ""
            if q2_1_clean and q2_2_clean:
                region = f"{q2_1_clean} {q2_2_clean}" 
            else:
                region = q2_1_clean or q2_2_clean 
            
            # [수정] 삽입 순서 변경 (birth_year, age)
            metadata_to_insert_list.append((mb_sn, mobile_carrier, gender, birth_year, age, region))

        print(f"  [Stage 3] 데이터 파싱 완료. {len(respondents_to_insert)}명, {len(metadata_to_insert_list)}개 메타데이터 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # (1) Respondents 삽입
            respondents_query = f"INSERT INTO {RESPONDENTS_TABLE} (mb_sn) VALUES %s ON CONFLICT (mb_sn) DO NOTHING;"
            execute_values(cur, respondents_query, list(respondents_to_insert))
            
            # (2) Metadata 삽입
            # [수정] INSERT 및 ON CONFLICT 구문 수정
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
            
            conn.commit() 
            print(f"  [Stage 3] Welcome 데이터 DB 저장 완료.")

        except psycopg2.Error as e:
            conn.rollback() 
            print(f"XXX [Stage 3] DB 저장 중 오류: {e}")

    except Exception as e:
        print(f"XXX [Stage 3] Welcome 데이터 처리 중 치명적 오류: {e}")
        conn.rollback() 

# --- 8. 메인 실행 함수 ---
def main():
    """스크립트의 메인 로직을 실행합니다."""
    
    conn = connect_to_db() 
    if not conn:
        return 

    try:
        # 2. 테이블 셋업 (없으면 생성)
        setup_master_tables(conn)

        print(f">>> [Phase 3] 입력 폴더 '{INPUT_FOLDER}' 스캔 시작...")
        
        found_welcome_file = False
        for filename in os.listdir(INPUT_FOLDER):
            if filename in WELCOME_FILES_TO_PROCESS:
                file_path = os.path.join(INPUT_FOLDER, filename)
                process_welcome_etl(conn, file_path)
                found_welcome_file = True
                break 
        
        if not found_welcome_file:
            print(f"  [Info] 처리 대상 Welcome 파일({', '.join(WELCOME_FILES_TO_PROCESS)})을 찾지 못했습니다.")
        
        print("\n>>> [Phase 4] Welcome ETL 작업 완료.")

    finally:
        if conn:
            conn.close()
            print(">>> [Phase 5] PostgreSQL DB 연결 종료.")

# --- 9. 스크립트 실행 ---
if __name__ == "__main__":
    main()