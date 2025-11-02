# -*- coding: utf-8 -*-
# 필요한 라이브러리들을 임포트합니다.
import psycopg2  # PostgreSQL DB 연결을 위한 라이브러리
from psycopg2.extras import execute_values  # 대량의 데이터를 효율적으로 삽입하기 위한 헬퍼 함수
import pandas as pd  # 엑셀(XLSX) 및 CSV 파일을 읽고 데이터를 다루기 위한 라이브러리
import os  # 파일 및 폴더 경로를 다루기 위한 라이브러리
from datetime import datetime # [신규] 나이 계산을 위해 datetime 임포트

# [안내] 이 스크립트는 pandas에서 XLSX 파일을 읽기 위해 'open_pyxl' 라이브러리가 필요합니다.
# 하지만 .csv 파일만 처리하도록 수정되었으므로, .csv 파일만 사용할 경우 'open_pyxl'이 필요하지 않습니다.
# (psycopg2-binary, pandas는 여전히 필요합니다)

# --- 설정 (Configuration) ---
# 스크립트 전역에서 사용될 설정 값들을 정의합니다.

# PostgreSQL 데이터베이스 연결 정보
DB_HOST = 'localhost'  # 데이터베이스 서버 주소
DB_PORT = '5432'       # 데이터베이스 포트
DB_NAME = 'capstone'   # 연결할 데이터베이스 이름
DB_USER = 'postgres'   # 데이터베이스 사용자 ID
DB_PASSWORD = 'Sjw@040107'  # 데이터베이스 비밀번호 (실제 환경에서는 보안에 유의)

# 원본 파일들이 들어있는 폴더 경로
INPUT_FOLDER = 'D:/capstone/Eternal/Data/db_insert/panelData/' 

# 처리할 Welcome 파일 이름 목록
WELCOME_FILES_TO_PROCESS = [
    'wel_1st.ex.csv'
]

# 마스터 테이블 이름 정의
RESPONDENTS_TABLE = 'respondents' # 응답자 고유 ID와 프로필 벡터를 저장할 테이블
METADATA_TABLE = 'metadata'       # 응답자의 고정 프로필(성별, 나이 등)을 저장할 테이블

# Welcome 데이터에서 '고유번호'로 사용될 컬럼 이름 후보 목록
ID_CANDIDATES = ['mb_sn', '고유번호', '패널ID', 'id']


# --- 1. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
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


# --- 2. Welcome용 마스터 테이블 셋업 함수 ---
def setup_master_tables(conn):
    """
    [수정] mb_sn을 기본 키로 사용하는 2개의 마스터 테이블을 (존재하지 않을 경우에만) 생성합니다.
    기존 테이블을 삭제(DROP)하지 않습니다.
    """
    
    try:
        with conn.cursor() as cur:
            # [수정] DROP TABLE 구문 삭제됨
            print("  [Info] 마스터 테이블 (respondents, metadata) 확인 및 (없으면) 생성 중...")
            
            # respondents 테이블의 기본 키를 'mb_sn'으로 변경
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (
                    mb_sn VARCHAR(255) PRIMARY KEY,
                    profile_vector TEXT DEFAULT NULL
                );
            """)
            
            # metadata 테이블이 'mb_sn'을 참조하도록 변경
            # [수정] age 컬럼의 VARCHAR 길이를 넉넉하게 (20 -> 50)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
                    metadata_id SERIAL PRIMARY KEY,
                    mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
                    mobile_carrier VARCHAR(100) DEFAULT NULL,
                    gender VARCHAR(10) DEFAULT NULL,
                    age VARCHAR(50) DEFAULT NULL, 
                    region VARCHAR(100) DEFAULT NULL
                );
            """)
            
            conn.commit()
        print(">>> [Phase 2] 마스터 테이블 2개 (respondents, metadata) 셋업 완료.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"XXX [Phase 2] 테이블 셋업 실패: {e}")
        raise  # 스크립트 중단

# --- 3. [신규] 헬퍼 함수 (데이터 변환용) ---

def calculate_age_format(birth_year_str):
    """ '1984' 같은 출생년도 문자열을 '1984년 (만 41세)' 형식으로 변환합니다. """
    if not birth_year_str or not str(birth_year_str).isdigit() or len(str(birth_year_str)) != 4:
        return str(birth_year_str) # 4자리 숫자가 아니면 원본 반환
    try:
        birth_year = int(birth_year_str)
        current_year = datetime.now().year
        # [수정] 한국식 만 나이 계산 (현재 년도 - 출생 년도)
        age = current_year - birth_year 
        return f"{birth_year}년 (만 {age}세)"
    except ValueError:
        return str(birth_year_str) # 변환 오류 시 원본 반환

def map_gender(gender_raw):
    """ 'M'/'F'를 '남성'/'여성'으로 변환합니다. """
    gender_str = str(gender_raw).strip().upper()
    if gender_str == 'M':
        return '남성'
    elif gender_str == 'F':
        return '여성'
    return gender_raw # 'M', 'F'가 아니면 원본 반환

# --- 4. Welcome 데이터 ETL 함수 ---
def process_welcome_etl(conn, file_path):
    """Welcome 파일(.xlsx 또는 .csv)을 파싱하여 respondents, metadata 테이블에 삽입/업데이트합니다."""
    print(f"  [Stage 3] '{file_path}'의 Welcome 데이터 처리 시작...")
    
    respondents_to_insert = set() # respondents 테이블용 (중복 제거)
    metadata_to_insert_list = []  # metadata 테이블용
    
    try:
        df_data = None
        # --- 파일 확장자에 따라 다르게 읽기 ---
        if file_path.endswith('.xlsx'):
            df_data = pd.read_excel(file_path, sheet_name=0, engine='open_pyxl')
        elif file_path.endswith('.csv'):
            try:
                df_data = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                print("  [Stage 3] UTF-8 디코딩 실패. CP949로 재시도...")
                df_data = pd.read_csv(file_path, encoding='cp949')
        
        if df_data is None:
            print("XXX [Stage 3] 지원하지 않는 파일 형식입니다.")
            return

        # --- 고유 ID 컬럼 찾기 ---
        id_column = None
        for col in ID_CANDIDATES:
            if col in df_data.columns:
                id_column = col
                break
        
        if id_column != 'mb_sn':
            print(f"  [Warning] DB 기본 키는 'mb_sn'이지만, CSV 파일에서 '{id_column}'을 ID로 사용합니다.")
            if 'mb_sn' in df_data.columns:
                 id_column = 'mb_sn' 
                 print(f"  [Info] 'mb_sn' 컬럼이 존재하여 기본 ID로 강제 사용합니다.")
            
        
        if not id_column:
            print(f"XXX [Stage 3] 고유 ID 컬럼({', '.join(ID_CANDIDATES)})을 찾을 수 없습니다. 이 파일을 건너뜁니다.")
            return

        print(f"  [Stage 3] 고유 ID 컬럼으로 '{id_column}'을 사용합니다.")

        # --- 데이터 추출 및 변환 ---
        for row in df_data.itertuples(index=False):
            row_dict = row._asdict()
            mb_sn = str(row_dict.get(id_column, '')).strip()
            
            if not mb_sn: continue 
            
            respondents_to_insert.add((mb_sn,))
            
            # [수정] mobile_carrier를 담당할 '구분' 열이 없으므로 None (NULL)으로 설정
            mobile_carrier = None 
            
            # [수정] gender 변환 로직 적용 (CSV 컬럼 'Q10' 사용)
            gender_raw = str(row_dict.get('Q10', '')).strip()
            gender = map_gender(gender_raw)
            
            # [수정] age 변환 로직 적용 (CSV 컬럼 'Q11' 사용)
            age_raw = str(row_dict.get('Q11', '')).strip() 
            age = calculate_age_format(age_raw)
            
            # [수정] region 변환 로직 (CSV 컬럼 'Q12_1', 'Q12_2' 사용)
            q2_1_clean = str(row_dict.get('Q12_1', '')).strip()
            q2_2_clean = str(row_dict.get('Q12_2', '')).strip()
            region = ""
            if q2_1_clean and q2_2_clean:
                region = f"{q2_1_clean} {q2_2_clean}"
            else:
                region = q2_1_clean or q2_2_clean
            
            # 변환된 데이터를 리스트에 추가
            metadata_to_insert_list.append((mb_sn, mobile_carrier, gender, age, region))

        print(f"  [Stage 3] 데이터 파싱 완료. {len(respondents_to_insert)}명, {len(metadata_to_insert_list)}개 메타데이터 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # respondents 삽입 SQL을 'mb_sn' 기준으로 변경
            respondents_query = f"INSERT INTO {RESPONDENTS_TABLE} (mb_sn) VALUES %s ON CONFLICT (mb_sn) DO NOTHING;"
            execute_values(cur, respondents_query, list(respondents_to_insert))
            
            # metadata 삽입 SQL을 'mb_sn' 기준으로 변경
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
            
            conn.commit()
            print(f"  [Stage 3] Welcome 데이터 DB 저장 완료.")

        except psycopg2.Error as e:
            conn.rollback()
            print(f"XXX [Stage 3] DB 저장 중 오류: {e}")

    except Exception as e:
        print(f"XXX [Stage 3] Welcome 데이터 처리 중 오류: {e}")
        conn.rollback()

# --- 5. 메인 실행 함수 ---
def main():
    """스크립트의 메인 로직을 실행합니다."""
    
    conn = connect_to_db()
    if not conn:
        return 

    try:
        setup_master_tables(conn)

        print(f">>> [Phase 3] 입력 폴더 '{INPUT_FOLDER}' 스캔 시작...")
        
        found_welcome_file = False
        for filename in os.listdir(INPUT_FOLDER):
            file_path = os.path.join(INPUT_FOLDER, filename)
            
            if filename in WELCOME_FILES_TO_PROCESS:
                # [오타 수정] file_Spath -> file_path
                process_welcome_etl(conn, file_path)
                found_welcome_file = True
                break 
        
        if not found_welcome_file:
            print(f"  [Info] 처리 대상 Welcome 파일({', '.join(WELCOME_FILES_TO_PROCESS)})을 찾지 못했습니다.")
        
        print("\n>>> [Phase 4] Welcome ETL 작업 완료.")

    finally:
        if conn:
            conn.close()
            print(">>> [Phase 5] PostgreSQL DB 연결 종료.")

# --- 스크립트 실행 ---
if __name__ == "__main__":
    main()

