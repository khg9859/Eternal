# -*- coding: utf-8 -*-
"""
A-Q Vector Embedding 스크립트 (v1.9 - DB Insert Bug Fix)

[v1.9 수정 사항]
- [Base] (사용자 요청) 'transformers' + 수동 'mean_pooling' 방식(v1.0)을 베이스로 사용.
- [Fix] (사용자 요청) 'KUREEmbeddingModel'이 인터넷("nlpai-lab/KURE-v1")에서 모델을
  직접 다운로드/로드하도록 'MODEL_PATH' (로컬 경로) 로직 제거.
- [Fix] (v1.8 유지) 'embed_answers' (Phase 4)의 'isdigit()' 로직 유지.
- [Fix] (v1.6 유지) 'pd.isna()'를 사용하여 ETL에서 누락된 NULL/NaN을 방어.

- [CRITICAL BUG FIX 1] (Phase 4 / ids_to_mark_zero):
    - 'zero_vector_str' (문자열)을 'zero_vector' (Python 리스트)로 수정.
    - (psycopg2는 vector 타입에 문자열이 아닌 리스트를 기대함)
- [CRITICAL BUG FIX 2] (Phase 3 / embed_codebooks):
    - SQL 쿼리의 'UPDATE ... SET q_vector = data.a_vector' 오타를
    - 'SET q_vector = data.q_vector'로 수정.
"""

# --- 1. 라이브러리 임포트 ---
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
import json
import os
import torch 
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv, find_dotenv 
import re 
import pandas as pd # (pd.isna()는 헬퍼가 아니므로 유지)

# --- 2. .env 파일 로드 ---
load_dotenv(find_dotenv())

# --- 3. 설정 (Configuration) ---
DB_HOST = os.getenv('DB_HOST','localhost') 
DB_PORT = os.getenv('DB_PORT','5432')
DB_NAME = os.getenv('DB_NAME') 
DB_USER = os.getenv('DB_USER','postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

if not all([DB_NAME, DB_PASSWORD]):
    print("XXX [오류] .env 파일에 DB_NAME 또는 DB_PASSWORD가 설정되지 않았습니다.")
    exit()

EMBEDDING_DIMENSION = 1024
BATCH_SIZE = 500 
MODEL_BATCH_SIZE = 32 

RESPONDENTS_TABLE = 'respondents'
ANSWERS_TABLE = 'answers'
CODEBOOKS_TABLE = 'codebooks'
METADATA_TABLE = 'metadata' 


# --- 4. 헬퍼 함수 (정제) ---
def clean_text_for_embedding(text):
    """(v1.1) KURE 모델에 넣기 전, 텍스트를 정제합니다."""
    if not text:
        return ""
    return str(text).strip()

# --- 5. KURE 임베딩 모델 클래스 (수동 Mean Pooling) ---
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] 
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

class KUREEmbeddingModel:
    """[v1.7] nlpai-lab/KURE-v1 모델을 (인터넷에서) 로드하고 임베딩을 수행하는 클래스"""
    def __init__(self, dimension): 
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"KUREEmbeddingModel: '{self.device}' 디바이스를 사용하여 모델을 로드합니다.")
            
            # [v1.7] 인터넷에서 모델 다운로드/로드
            self.tokenizer = AutoTokenizer.from_pretrained("nlpai-lab/KURE-v1")
            self.model = AutoModel.from_pretrained("nlpai-lab/KURE-v1").to(self.device)
            self.model.eval() 
            
            print(f"KUREEmbeddingModel: 'nlpai-lab/KURE-v1' 모델 로드 성공.")
            
            if self.model.config.hidden_size != dimension:
                print(f"[경고] 설정된 EMBEDDING_DIMENSION({dimension})과 모델의 hidden_size({self.model.config.hidden_size})가 다릅니다!")
                exit()
            
        except OSError as e:
            print(f"XXX [오류] 모델 다운로드/로드 실패: {e}")
            print(f"XXX (참고) 인터넷 연결이 불안정하거나, Hugging Face 서버 문제일 수 있습니다.")
            exit()
        except Exception as e:
            print(f"XXX KUREEmbeddingModel: 모델 로드 중 심각한 오류 발생: {e}")
            print(f"XXX (참고) 'tf_keras' 오류의 경우, (myenv) 환경의 PyTorch/TensorFlow 충돌 문제입니다.")
            raise e

    def get_embeddings(self, text_list):
        """[v1.0] 텍스트 리스트를 받아 임베딩 벡터 리스트(NumPy Array)를 반환합니다."""
        all_vectors = []
        
        for i in range(0, len(text_list), MODEL_BATCH_SIZE):
            batch_texts = text_list[i : i + MODEL_BATCH_SIZE]
            
            cleaned_texts = [clean_text_for_embedding(t) for t in batch_texts]

            encoded_input = self.tokenizer(
                cleaned_texts, 
                padding=True, 
                truncation=True, 
                return_tensors='pt', 
                max_length=512
            ).to(self.device)
            
            with torch.no_grad():
                model_output = self.model(**encoded_input)
            
            sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
            all_vectors.extend(sentence_embeddings.cpu().numpy())
            
        return all_vectors

# --- 6. DB 연결 함수 ---
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

# --- 7. 벡터 컬럼 셋업 함수 ---
def setup_vector_columns(conn):
    """(v1.0) A/Q/P 벡터를 저장할 컬럼을 (DROP/ADD) 셋업합니다."""
    print("\n>>> [Phase 2] 벡터 컬럼(q_vector, a_vector, profile_vector) 셋업 시작...")
    
    queries = [
        f"ALTER TABLE {CODEBOOKS_TABLE} DROP COLUMN IF EXISTS q_vector;",
        f"ALTER TABLE {CODEBOOKS_TABLE} ADD COLUMN q_vector VECTOR({EMBEDDING_DIMENSION});",
        f"ALTER TABLE {ANSWERS_TABLE} DROP COLUMN IF EXISTS a_vector;",
        f"ALTER TABLE {ANSWERS_TABLE} ADD COLUMN a_vector VECTOR({EMBEDDING_DIMENSION});",
        f"ALTER TABLE {RESPONDENTS_TABLE} DROP COLUMN IF EXISTS profile_vector;",
        f"ALTER TABLE {RESPONDENTS_TABLE} ADD COLUMN profile_vector VECTOR({EMBEDDING_DIMENSION});"
    ]
    
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            for query in queries:
                cur.execute(query)
            conn.commit()
        print(">>> [Phase 2] 모든 벡터 컬럼 셋업 완료.")
    except Exception as e:
        print(f"XXX [Phase 2] 벡터 컬럼 셋업 중 오류 발생: {e}")
        conn.rollback()
        raise 

# --- 8. Codebook (질문) 임베딩 함수 (Phase 3) ---
def embed_codebooks(conn, model):
    """(v1.0) codebooks 테이블의 'q_title'을 임베딩하여 'q_vector'에 저장합니다."""
    print("\n>>> [Phase 3] Codebook (질문) 임베딩 시작...")
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT codebook_id, codebook_data ->> 'q_title' FROM {CODEBOOKS_TABLE} WHERE q_vector IS NULL;")
        rows = cur.fetchall()
        
        if not rows:
            print("  [Info] 새로 임베딩할 질문(q_vector)이 없습니다.")
            return

        print(f"  [Info] 총 {len(rows)}개의 신규 질문을 임베딩합니다.")
        
        texts_to_embed = [row[1] for row in rows if row[1]] 
        ids_to_update = [row[0] for row in rows if row[1]]
        
        if not texts_to_embed:
            print("  [Info] 임베딩할 q_title 텍스트가 없습니다.")
            return

        vectors = model.get_embeddings(texts_to_embed)
        print(f"  [Embedding API] {len(texts_to_embed)}개 텍스트 임베딩 완료.") 
        
        update_data = [(v.tolist(), id_val) for v, id_val in zip(vectors, ids_to_update)]

        if update_data:
            # [CRITICAL BUG FIX 2] (v1.9)
            # 'data.a_vector' -> 'data.q_vector'로 오타 수정
            # 'AS data (a_vector, ...)' -> 'AS data (q_vector, ...)'로 오타 수정
            update_query = f"""
                UPDATE {CODEBOOKS_TABLE} SET q_vector = data.q_vector
                FROM (VALUES %s) AS data (q_vector, codebook_id)
                WHERE {CODEBOOKS_TABLE}.codebook_id = data.codebook_id;
            """
            execute_values(cur, update_query, update_data, page_size=BATCH_SIZE)
            conn.commit()
            print(f"  [Success] 총 {len(update_data)}개의 질문 벡터(q_vector) 저장 완료.")

    except Exception as e:
        print(f"  XXX [Phase 3] Codebook 임베딩 중 오류 발생: {e}")
        conn.rollback()
    finally:
        cur.close()

# --- 9. Answers (답변) 임베딩 함수 (Phase 4) ---
def embed_answers(conn, model):
    """
    [v1.8] answers 테이블의 답변을 임베딩합니다.
    (사용자 로직: "isdigit()이냐 아니냐"로 객관식/주관식 분류)
    """
    print("\n>>> [Phase 4] Answers (답변) 임베딩 시작...")
    cur = conn.cursor()
    try:
        total_processed = 0
        
        while True:
            print(f"  [Info] DB에서 임베딩할 답변 {BATCH_SIZE}개 조회 시도 (Total: {total_processed})...")
            
            query = f"""
                SELECT 
                    a.answer_id, 
                    a.answer_value, 
                    c.codebook_data
                FROM {ANSWERS_TABLE} AS a
                JOIN {CODEBOOKS_TABLE} AS c ON a.question_id = c.codebook_id
                WHERE a.a_vector IS NULL
                LIMIT {BATCH_SIZE}; 
            """
            
            cur.execute(query)
            rows = cur.fetchall()
            
            if not rows:
                print("  [Info] 새로 임베딩할 답변이 더 이상 없습니다.")
                break # 루프 종료

            print(f"  [Info] {len(rows)}개의 신규 답변을 처리합니다. 임베딩할 텍스트 추출 중...")

            tasks = [] # (text_to_embed, answer_id) : 실제 임베딩 대상
            ids_to_mark_zero = [] # (answer_id,) : 영벡터 처리 대상

            for row in rows:
                answer_id, answer_value_raw, codebook_data = row
                
                if pd.isna(answer_value_raw):
                    ids_to_mark_zero.append((answer_id,))
                    continue
                
                answer_value = str(answer_value_raw).strip() 
                
                if not answer_value or not codebook_data:
                    ids_to_mark_zero.append((answer_id,))
                    continue

                text_to_embed = None

                if answer_value.isdigit():
                    # --- [숫자] (객관식 또는 Numeric) ---
                    choices = codebook_data.get('answers', [])
                    
                    # [수정] choices가 있는지 확인하는 분기 추가
                    if choices:
                        # --- 1. [객관식] (Choices 리스트가 있음) ---
                        found_match = False
                        if choices: # (이중 체크지만 안전을 위해 둠)
                            for choice in choices:
                                qi_val_str = str(choice.get('qi_val')).strip()
                                if qi_val_str == answer_value:
                                    text_to_embed = str(choice.get('qi_title')).strip() 
                                    found_match = True
                                    break
                        
                        if found_match and text_to_embed:
                            tasks.append((text_to_embed, answer_id))
                        else:
                            # 객관식인데 매칭되는 보기가 없음 (e.g. '99')
                            ids_to_mark_zero.append((answer_id,))
                    
                    else:
                        # --- 2. [숫자형] (Choices 리스트가 비어있음) ---
                        # "자녀수" + "2" => "자녀수 2" 조합
                        q_title = codebook_data.get('q_title')
                        if q_title:
                            text_to_embed = f"{str(q_title).strip()} {answer_value}"
                            tasks.append((text_to_embed, answer_id))
                        else:
                            # q_title도 없는 비정상 데이터
                            ids_to_mark_zero.append((answer_id,))
                
                else:
                    # --- [텍스트] (주관식) ---
                    text_to_embed = answer_value 
                    tasks.append((text_to_embed, answer_id))

            
            if not tasks and not ids_to_mark_zero:
                continue 
                
            print(f"  [Info] {len(rows)}개 중 {len(tasks)}개의 텍스트 답변 임베딩 / {len(ids_to_mark_zero)}개는 영벡터(Zero)로 표시.")

            # --- 일괄 임베딩 및 DB 업데이트 ---
            if tasks:
                texts_to_embed = [task[0] for task in tasks]
                ids_to_update = [task[1] for task in tasks]
                
                vectors = model.get_embeddings(texts_to_embed)
                print(f"  [Embedding API] {len(texts_to_embed)}개 텍스트 임베딩 완료.") 
                
                update_data = [(v.tolist(), id_val) for v, id_val in zip(vectors, ids_to_update)]

                update_query = f"""
                    UPDATE {ANSWERS_TABLE} SET a_vector = data.a_vector
                    FROM (VALUES %s) AS data (a_vector, answer_id)
                    WHERE {ANSWERS_TABLE}.answer_id = data.answer_id;
                """
                execute_values(cur, update_query, update_data, page_size=BATCH_SIZE)
            
            if ids_to_mark_zero:
                # [CRITICAL BUG FIX 1] (v1.9)
                # 'zero_vector_str' (문자열) -> 'zero_vector' (리스트)로 수정
                zero_vector = [0.0] * EMBEDDING_DIMENSION
                update_data_zero = [(zero_vector, id_val[0]) for id_val in ids_to_mark_zero]
                
                update_query_zero = f"""
                    UPDATE {ANSWERS_TABLE} SET a_vector = data.a_vector
                    FROM (VALUES %s) AS data (a_vector, answer_id)
                    WHERE {ANSWERS_TABLE}.answer_id = data.answer_id;
                """
                execute_values(cur, update_query_zero, update_data_zero, page_size=BATCH_SIZE)

            conn.commit() 
            total_processed += len(rows)
        
        print(f"\n  [Success] 총 {total_processed}개의 답변 벡터(a_vector) 처리 완료.")

    except Exception as e:
        print(f"  XXX [Phase 4] Answers 임베딩 중 오류 발생: {e}")
        conn.rollback()
    finally:
        cur.close()


# --- 10. 메인 실행 파이프라인 ---
def main():
    print("===== A/Q 벡터 임베딩 파이프라인 시작 =====")
    
    try:
        # [v1.7] 인터넷에서 모델 로드
        model = KUREEmbeddingModel(dimension=EMBEDDING_DIMENSION)
    except Exception as e:
        print("XXX 모델 초기화 실패. 스크립트를 종료합니다.")
        return

    db_conn = connect_to_db() 
    if db_conn:
        try:
            setup_vector_columns(db_conn)
            embed_codebooks(db_conn, model)
            #embed_answers(db_conn, model)
            
            print("\n[Info] A-Vector 및 Q-Vector 생성이 완료되었습니다.")

            print("\n>>> [Success] 모든 임베딩 작업이 완료되었습니다.")

        except Exception as e:
            print(f"XXX 메인 실행 중 치명적 오류 발생: {e}")
            db_conn.rollback()
        finally:
            db_conn.close()
            print(">>> [Phase 6] PostgreSQL DB 연결 종료.")

# --- 스크립트 실행 ---
if __name__ == '__main__':
    main()