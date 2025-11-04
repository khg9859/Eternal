# -*- coding: utf-8 -*-
"""
Welcome 1st ETL 스크립트 (Append-Only 버전)

이 스크립트는 'Welcome_1st' 데이터를 (CSV 또는 XLSX) 읽어와서
PostgreSQL 데이터베이스의 'respondents'와 'metadata' 테이블에 삽입(Append)합니다.

주요 기능:
1. .env 파일을 통해 DB 접속 정보를 안전하게 로드합니다.
2. 'respondents', 'metadata' 테이블이 없으면 생성합니다. (IF NOT EXISTS)
    - [중요] 기존 데이터를 보존하기 위해 테이블을 삭제(DROP)하지 않습니다.
3. 'Welcome_1st' 데이터의 원본 컬럼(Q10, Q11 등)을 'gender', 'age' 등
    표준화된 메타데이터로 변환합니다.
4. 'respondents' 테이블에는 새 사용자를 추가하고 (ON CONFLICT DO NOTHING),
    'metadata' 테이블에는 데이터를 덮어쓰거나(UPDATE) 추가합니다 (COALESCE 사용).
"""

# --- 1. 라이브러리 임포트 ---
import psycopg2 # PostgreSQL DB 어댑터
from psycopg2.extras import execute_values # 대량 INSERT를 위한 psycopg2 헬퍼
import pandas as pd # 데이터 분석 및 CSV/XLSX 파일 읽기용 라이브러리
from datetime import datetime # '만 나이' 계산을 위해 현재 년도 확인용
from dotenv import load_dotenv,find_dotenv  # .env 파일에서 환경 변수를 로드하기 위함
import os # .env 값(환경 변수)을 읽고, 파일 경로를 다루기 위함

# --- 2. .env 파일 로드 ---
# [필수] 스크립트 시작 시 .env 파일에 정의된 변수들을
# '환경 변수'로 로드합니다.
# 이 코드(load_dotenv())가 실행된 *이후*부터 os.getenv()가 .env 값을 읽을 수 있습니다.


load_dotenv(find_dotenv())

# --- 3. 설정 (Configuration) ---
# 스크립트 전역에서 사용될 설정 값들을 정의합니다.

# PostgreSQL 데이터베이스 연결 정보
# os.getenv('KEY', 'DEFAULT') 형식:
# 1. .env 파일에서 'KEY'를 찾습니다.
# 2. .env 파일에 'KEY'가 없으면 'DEFAULT' 값을 사용합니다.
DB_HOST = os.getenv('DB_HOST','localhost') 
DB_PORT = os.getenv('DB_PORT','5432')
# .env 파일에 'DB_NAME'이 없으면 None이 됩니다.
DB_NAME = os.getenv('DB_NAME') 
DB_USER = os.getenv('DB_USER','postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# 원본 파일들이 들어있는 폴더 경로
INPUT_FOLDER = os.getenv('INPUT_PATH')

# [방어 코드] 스크립트 실행에 필수적인 값들이 .env에 없는 경우,
# 명확한 오류 메시지를 주고 즉시 종료합니다.
if not all([DB_NAME, DB_PASSWORD, INPUT_FOLDER]):
    print("XXX [오류] .env 파일에 DB_NAME, DB_PASSWORD, INPUT_PATH 중 하나 이상이 설정되지 않았습니다.")
    print("XXX 스크립트와 같은 경로에 .env 파일이 있는지 확인하세요.")
    exit() # 스크립트 강제 종료

# 이 스크립트가 처리할 Welcome 파일의 정확한 이름
WELCOME_FILES_TO_PROCESS = [
    'wel_1st.ex.csv'
]

# 마스터 테이블 이름 정의 (다른 스크립트와 일관성 유지)
RESPONDENTS_TABLE = 'respondents' 
METADATA_TABLE = 'metadata' 

# Welcome 데이터에서 '고유번호'로 사용될 컬럼 이름 후보 목록
# (파일마다 'mb_sn', '고유번호' 등 다를 수 있으므로 리스트로 관리)
ID_CANDIDATES = ['mb_sn', '고유번호', '패널ID', 'id']

# --- 4. DB 연결 함수 ---
def connect_to_db():
    """PostgreSQL 마스터 데이터베이스에 연결합니다."""
    print(">>> [Phase 1] PostgreSQL DB 연결 시도...")
    try:
        # 설정 값을 사용하여 DB 연결을 시도합니다.
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print(">>> [Phase 1] PostgreSQL DB 연결 성공.")
        return conn # 연결 객체(conn)를 반환합니다.
    except psycopg2.Error as e:
        # DB 연결 자체에 실패한 경우 (비밀번호 오류, DB 없음, 서버 다운 등)
        print(f"XXX [Phase 1] DB 연결 실패: {e}")
        return None

# --- 5. 마스터 테이블 셋업 함수 ---
def setup_master_tables(conn):
    """
    [Append-Only] respondents, metadata 테이블이 없으면 생성합니다.
    (qpoll, welcome_2nd 데이터 보존을 위해 DROP하지 않습니다.)
    """
    
    try:
        # conn.cursor()를 'with' 구문과 함께 사용하면
        # 작업이 끝나거나 오류 발생 시 자동으로 cur.close()를 호출해 줍니다.
        with conn.cursor() as cur:
            
            print("  [Info] 마스터 테이블 (respondents, metadata) 확인 및 (없으면) 생성 중...")
            
            # 1. respondents 테이블 생성 (IF NOT EXISTS)
            # 'IF NOT EXISTS' 구문: 테이블이 이미 존재하면 이 쿼리를 무시합니다.
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {RESPONDENTS_TABLE} (
                    mb_sn VARCHAR(255) PRIMARY KEY, -- 'mb_sn'을 기본 키로 설정
                    profile_vector TEXT DEFAULT NULL -- (임베딩 스크립트가 채울 P-벡터 컬럼)
                );
            """)
            
            # 2. metadata 테이블 생성 (IF NOT EXISTS)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {METADATA_TABLE} (
                    metadata_id SERIAL PRIMARY KEY, -- 행 고유 ID (자동 증가)
                    -- mb_sn: respondents 테이블의 mb_sn을 참조하는 외래 키(FK)
                    -- ON DELETE CASCADE: respondents에서 mb_sn이 삭제되면, metadata의 해당 행도 자동 삭제
                    mb_sn VARCHAR(255) NOT NULL UNIQUE REFERENCES {RESPONDENTS_TABLE}(mb_sn) ON DELETE CASCADE,
                    mobile_carrier VARCHAR(100) DEFAULT NULL,
                    gender VARCHAR(10) DEFAULT NULL,
                    age VARCHAR(50) DEFAULT NULL, -- '1984년 (만 41세)' 같은 긴 텍스트 저장을 위해 50으로 설정
                    region VARCHAR(100) DEFAULT NULL
                );
            """)
            
            # 모든 CREATE TABLE 작업이 성공했을 때만 DB에 최종 반영
            conn.commit()
        print(">>> [Phase 2] 마스터 테이블 2개 (respondents, metadata) 셋업 완료.")
    
    except psycopg2.Error as e:
        conn.rollback() # 테이블 생성 중 오류 발생 시, 모든 변경 사항 롤백
        print(f"XXX [Phase 2] 테이블 셋업 실패: {e}")
        raise # 이 오류를 상위(main)로 전달하여 스크립트 중단

# --- 6. 헬퍼 함수 (데이터 변환용) ---

def calculate_age_format(birth_year_str):
    """ '1984' 같은 출생년도 문자열을 '1984년 (만 41세)' 형식으로 변환합니다. """
    
    # 입력값이 4자리 숫자가 아니면 (예: 'NULL', '39', '모름') 변환하지 않고 원본 반환
    if not birth_year_str or not str(birth_year_str).isdigit() or len(str(birth_year_str)) != 4:
        return str(birth_year_str) 
    try:
        birth_year = int(birth_year_str)
        current_year = datetime.now().year
        # (현재 년도 - 출생 년도)로 '만 나이' 계산
        age = current_year - birth_year 
        return f"{birth_year}년 (만 {age}세)"
    except ValueError:
        return str(birth_year_str) # int 변환 중 오류 시 원본 반환

def map_gender(gender_raw):
    """ 'M'/'F'를 '남성'/'여성'으로 변환합니다. """
    gender_str = str(gender_raw).strip().upper() # 소문자 m, 공백 등을 제거
    if gender_str == 'M':
        return '남성'
    elif gender_str == 'F':
        return '여성'
    return gender_raw # 'M', 'F'가 아니면(예: '남', '여') 원본 반환

# --- 7. Welcome 데이터 ETL 함수 ---
def process_welcome_etl(conn, file_path):
    """Welcome 파일을 파싱하여 respondents, metadata 테이블에 삽입/업데이트합니다."""
    print(f"  [Stage 3] '{file_path}'의 Welcome 데이터 처리 시작...")
    
    respondents_to_insert = set() # respondents 테이블용 (set을 사용해 mb_sn 자동 중복 제거)
    metadata_to_insert_list = []  # metadata 테이블용 (execute_values에 사용할 리스트)
    
    try:
        df_data = None # 데이터를 담을 DataFrame 초기화
        
        # --- 파일 확장자에 따라 다르게 읽기 ---
        if file_path.endswith('.xlsx'):
            # .xlsx 파일은 'open_pyxl' 엔진 필요
            df_data = pd.read_excel(file_path, sheet_name=0, engine='open_pyxl')
        elif file_path.endswith('.csv'):
            try:
                # 1. 기본 인코딩인 'utf-8'로 읽기 시도
                df_data = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                # 2. 'utf-8' 실패 시 (Windows 환경 Excel 저장), 'cp949'로 재시도
                print("  [Stage 3] UTF-8 디코딩 실패. CP949로 재시도...")
                df_data = pd.read_csv(file_path, encoding='cp949')
        
        if df_data is None:
            print("XXX [Stage 3] 지원하지 않는 파일 형식입니다. (CSV 또는 XLSX만 가능)")
            return

        # --- 고유 ID 컬럼 찾기 (파일마다 이름이 다를 수 있음) ---
        id_column = None
        for col in ID_CANDIDATES: # ['mb_sn', '고유번호', ...]
            if col in df_data.columns:
                id_column = col # 파일의 컬럼명 중 후보 목록에 있는 첫 번째 컬럼을 ID로 사용
                break
        
        # (qpoll 스크립트와 mb_sn을 통일하기 위한 로직)
        if id_column != 'mb_sn':
            print(f"  [Warning] DB 기본 키는 'mb_sn'이지만, CSV 파일에서 '{id_column}'을 ID로 사용합니다.")
            # 만약 'mb_sn' 컬럼이 *존재하는데도* '고유번호'가 먼저 잡혔다면, 'mb_sn'을 강제로 사용
            if 'mb_sn' in df_data.columns:
                 id_column = 'mb_sn' 
                 print(f"  [Info] 'mb_sn' 컬럼이 존재하여 기본 ID로 강제 사용합니다.")
                 
        if not id_column:
            print(f"XXX [Stage 3] 고유 ID 컬럼({', '.join(ID_CANDIDATES)})을 찾을 수 없습니다. 이 파일을 건너뜁니다.")
            return

        print(f"  [Stage 3] 고유 ID 컬럼으로 '{id_column}'을 사용합니다.")

        # --- 데이터 추출 및 변환 (Pandas DataFrame 순회) ---
        # itertuples(): DataFrame을 한 행(row)씩 순회 (index=False: pandas 인덱스 제외)
        for row in df_data.itertuples(index=False):
            row_dict = row._asdict() # 현재 행을 딕셔너리(컬럼명: 값)로 변환
            mb_sn = str(row_dict.get(id_column, '')).strip() # ID 컬럼의 값을 문자열로 추출
            
            if not mb_sn: continue # mb_sn이 없는 행은 무시
            
            # (1) respondents 테이블용 데이터: set에 (mb_sn,) 튜플 추가
            respondents_to_insert.add((mb_sn,))
            
            # (2) metadata 테이블용 데이터 변환
            
            # 'welcome_1st'에는 통신사('구분') 데이터가 없으므로 None으로 설정
            mobile_carrier = None 
            
            # 'Q10' 컬럼(성별) 값을 '남성'/'여성'으로 변환
            gender_raw = str(row_dict.get('Q10', '')).strip()
            gender = map_gender(gender_raw)
            
            # 'Q11' 컬럼(출생년도) 값을 '1984년 (만 41세)' 형식으로 변환
            age_raw = str(row_dict.get('Q11', '')).strip() 
            age = calculate_age_format(age_raw)
            
            # 'Q12_1'(시/도)과 'Q12_2'(시/군/구)를 '서울특별시 동대문구' 형식으로 조합
            q2_1_clean = str(row_dict.get('Q12_1', '')).strip()
            q2_2_clean = str(row_dict.get('Q12_2', '')).strip()
            region = ""
            if q2_1_clean and q2_2_clean:
                region = f"{q2_1_clean} {q2_2_clean}" # 둘 다 있으면 공백으로 연결
            else:
                region = q2_1_clean or q2_2_clean # 둘 중 하나만 있으면 그 값 사용
            
            # 변환된 데이터를 튜플 형태로 리스트에 추가 (DB 삽입 순서와 일치해야 함)
            metadata_to_insert_list.append((mb_sn, mobile_carrier, gender, age, region))

        print(f"  [Stage 3] 데이터 파싱 완료. {len(respondents_to_insert)}명, {len(metadata_to_insert_list)}개 메타데이터 감지.")

        # --- DB에 삽입 ---
        cur = conn.cursor()
        try:
            # (1) Respondents 삽입
            # 'ON CONFLICT (mb_sn) DO NOTHING':
            #   mb_sn(PK)이 이미 DB에 존재하면(qpoll이나 welcome_2nd에서 삽입됨) 무시.
            #   새로운 mb_sn만 삽입됩니다. (Append-Only)
            respondents_query = f"INSERT INTO {RESPONDENTS_TABLE} (mb_sn) VALUES %s ON CONFLICT (mb_sn) DO NOTHING;"
            # execute_values: respondents_to_insert (리스트)의 데이터를 한 번의 쿼리로 대량 삽입
            execute_values(cur, respondents_query, list(respondents_to_insert))
            
            # (2) Metadata 삽입
            # 'ON CONFLICT (mb_sn) DO UPDATE SET ...':
            #   mb_sn(UNIQUE)이 이미 DB에 존재하면(qpoll에서 삽입됨), UPDATE 수행
            #   mb_sn이 없으면, INSERT 수행
            metadata_query = f"""
                INSERT INTO {METADATA_TABLE} (mb_sn, mobile_carrier, gender, age, region)
                VALUES %s
                ON CONFLICT (mb_sn) DO UPDATE SET
                    -- [중요] COALESCE(A, B): A가 NULL이 아니면 A, A가 NULL이면 B
                    -- (qpoll에서 이미 'SKT'를 삽입했다면) COALESCE('SKT', NULL) -> 'SKT' (기존 값 유지)
                    -- (qpoll에서 NULL이었고, welcome_1st가 '남성'을 삽입하면) COALESCE(NULL, '남성') -> '남성' (새 값으로 갱신)
                    mobile_carrier = COALESCE({METADATA_TABLE}.mobile_carrier, EXCLUDED.mobile_carrier),
                    gender = COALESCE({METADATA_TABLE}.gender, EXCLUDED.gender),
                    age = COALESCE({METADATA_TABLE}.age, EXCLUDED.age),
                    region = COALESCE({METADATA_TABLE}.region, EXCLUDED.region);
            """
            execute_values(cur, metadata_query, metadata_to_insert_list)
            
            conn.commit() # (1)과 (2)가 모두 성공했을 때만 DB에 최종 반영
            print(f"  [Stage 3] Welcome 데이터 DB 저장 완료.")

        except psycopg2.Error as e:
            conn.rollback() # DB 저장 중 오류 (예: FK 제약조건 위배) 시 롤백
            print(f"XXX [Stage 3] DB 저장 중 오류: {e}")

    except Exception as e:
        # 파일 읽기(read_csv) 또는 데이터 변환(for row...) 중 발생한 예외
        print(f"XXX [Stage 3] Welcome 데이터 처리 중 치명적 오류: {e}")
        conn.rollback() # 혹시 모를 변경 사항 롤백

# --- 8. 메인 실행 함수 ---
def main():
    """스크립트의 메인 로직을 실행합니다."""
    
    conn = connect_to_db() # 1. DB 연결
    if not conn:
        return # DB 연결 실패 시 즉시 종료

    try:
        # 2. 테이블 셋업 (없으면 생성)
        setup_master_tables(conn)

        print(f">>> [Phase 3] 입력 폴더 '{INPUT_FOLDER}' 스캔 시작...")
        
        found_welcome_file = False
        # 3. INPUT_FOLDER의 모든 파일을 순회
        for filename in os.listdir(INPUT_FOLDER):
            # 파일 이름이 WELCOME_FILES_TO_PROCESS 리스트에 있는지 확인
            if filename in WELCOME_FILES_TO_PROCESS:
                file_path = os.path.join(INPUT_FOLDER, filename)
                # 4. 일치하는 파일을 찾으면 ETL 함수 호출
                process_welcome_etl(conn, file_path)
                found_welcome_file = True
                break # Welcome 파일은 하나만 처리하고 종료
        
        if not found_welcome_file:
            print(f"  [Info] 처리 대상 Welcome 파일({', '.join(WELCOME_FILES_TO_PROCESS)})을 찾지 못했습니다.")
        
        print("\n>>> [Phase 4] Welcome ETL 작업 완료.")

    finally:
        # 5. 스크립트가 성공하든, 오류로 중단되든 항상 DB 연결을 닫습니다.
        if conn:
            conn.close()
            print(">>> [Phase 5] PostgreSQL DB 연결 종료.")

# --- 9. 스크립트 실행 ---
# 'python welcome_1st_etl.py'로 직접 실행되었을 때만 main() 함수를 호출
if __name__ == "__main__":
    main()

