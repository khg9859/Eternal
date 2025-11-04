# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# EMBEDDING SCRIPT
# -----------------------------------------------------------------
# 이 스크립트는 PostgreSQL DB에 연결하여 3가지 작업을 수행합니다:
# 1. 'codebooks' 테이블의 질문 제목을 임베딩하여 'q_vector'에 저장
# 2. 'answers' 테이블의 답변을 임베딩하여 'a_vector'에 저장
#    - 객관식: 코드북의 보기 텍스트 (예: '미혼')
#    - 주관식: 원본 답변 텍스트 (예: 'K5', '너무 비싸요')
# 3. 'respondents' 테이블에 사용자별 통합 프로필 벡터를 생성하여 저장
#
# [요구 라이브러리]
# pip install psycopg2-binary numpy pandas transformers torch
#
# [DB 사전 설정]
# 이 스크립트를 실행하기 전에 PostgreSQL에 'vector' 확장이 설치되어 있어야 합니다.
# (DB 슈퍼유저로 접속하여 `CREATE EXTENSION IF NOT EXISTS vector;` 실행)
# -----------------------------------------------------------------

import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import json
import os
import numpy as np  # 임베딩 벡터 계산용
import time
import torch # [신규] PyTorch
from transformers import AutoTokenizer, AutoModel # [신규] Transformers

# --- 설정 (Configuration) ---
DB_HOST = os.getenv('DB_HOST','localhost') # 데이터베이스 서버 주소 ##보안을 신경 쓰지 않으면 = DB_HOST='' 식으로 사용가능
DB_PORT = os.getenv('DB_PORT','5432')    # 데이터베이스 포트
DB_NAME = os.getenv('DB_NAME')   # 연결할 데이터베이스 이름
DB_USER = os.getenv('DB_USER','postgres')   # 데이터베이스 사용자 ID
DB_PASSWORD = os.getenv('DB_PASSWORD')  # 데이터베이스 비밀번호 (실제 환경에서는 보안에 유의)

# [수정] 임베딩 모델의 차원 (KURE-v1은 1024)
EMBEDDING_DIMENSION = 1024
# DB에 한 번에 업데이트할 배치 크기
BATCH_SIZE = 500
# 임베딩 모델 API에 한 번에 보낼 텍스트 배치 크기
MODEL_BATCH_SIZE = 32 

# --- 테이블 이름 (ETL 스크립트와 동일해야 함) ---
RESPONDENTS_TABLE = 'respondents'
ANSWERS_TABLE = 'answers'
CODEBOOKS_TABLE = 'codebooks'
METADATA_TABLE = 'metadata'

# --- [신규] KURE-v1 모델 로딩 ---

# KURE-v1 README에서 권장하는 Mean Pooling 함수
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] # First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

class KUREEmbeddingModel:
    """nlpai-lab/KURE-v1 모델을 로드하고 임베딩을 수행하는 클래스"""
    def __init__(self, dimension):
        try:
            # GPU 사용 가능 여부 확인
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"KUREEmbeddingModel: '{self.device}' 디바이스를 사용하여 모델을 로드합니다.")
            
            self.tokenizer = AutoTokenizer.from_pretrained("nlpai-lab/KURE-v1")
            self.model = AutoModel.from_pretrained("nlpai-lab/KURE-v1").to(self.device)
            self.model.eval() # 평가 모드로 설정 (Dropout 등 비활성화)
            
            print(f"KUREEmbeddingModel: 'nlpai-lab/KURE-v1' 모델 로드 성공.")
            
            # 모델 차원 확인 (설정값과 다를 경우 경고)
            if self.model.config.hidden_size != dimension:
                 print(f"[경고] 설정된 EMBEDDING_DIMENSION({dimension})과 모델의 hidden_size({self.model.config.hidden_size})가 다릅니다!")
                 # (필요시) EMBEDDING_DIMENSION = self.model.config.hidden_size 로 강제 설정 가능
            
        except Exception as e:
            print(f"XXX KUREEmbeddingModel: 모델 로드 중 심각한 오류 발생: {e}")
            print("스크립트를 중단합니다. 'pip install transformers torch'가 올바르게 실행되었는지 확인하세요.")
            raise e

    def get_embeddings(self, text_list):
        """텍스트 리스트를 받아 임베딩 벡터 리스트(NumPy Array)를 반환합니다."""
        all_vectors = []
        
        # [신규] 텍스트가 너무 많을 경우, 모델 배치 크기(MODEL_BATCH_SIZE)만큼 나누어 처리
        for i in range(0, len(text_list), MODEL_BATCH_SIZE):
            batch_texts = text_list[i : i + MODEL_BATCH_SIZE]
            
            # 1. 토크나이징
            encoded_input = self.tokenizer(
                batch_texts, 
                padding=True, 
                truncation=True, 
                return_tensors='pt', 
                max_length=512 # KURE-v1의 최대 길이
            ).to(self.device)
            
            # 2. 모델 추론 (Gradient 계산 안 함)
            with torch.no_grad():
                model_output = self.model(**encoded_input)
            
            # 3. Mean Pooling (문장 벡터 추출)
            sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
            
            # 4. CPU로 이동 및 NumPy 변환 (psycopg2가 인식할 수 있도록)
            all_vectors.extend(sentence_embeddings.cpu().numpy())
            
        print(f"  [Embedding API] {len(text_list)}개 텍스트 임베딩 완료.")
        return all_vectors

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

# --- 2. [신규] 벡터 컬럼 준비 함수 ---
def setup_vector_columns(conn):
    """임베딩 벡터를 저장할 컬럼을 테이블에 추가(또는 재생성)합니다."""
    print(">>> [Phase 2] 벡터 컬럼(q_vector, a_vector, profile_vector) 셋업 시작...")
    cur = conn.cursor()
    try:
        # 0. pgvector 확장 활성화
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # 1. codebooks (질문 벡터)
        # [수정] ADD IF NOT EXISTS 대신 DROP + ADD로 변경
        cur.execute(f"""
            ALTER TABLE {CODEBOOKS_TABLE} 
            DROP COLUMN IF EXISTS q_vector;
        """)
        cur.execute(f"""
            ALTER TABLE {CODEBOOKS_TABLE} 
            ADD COLUMN q_vector VECTOR({EMBEDDING_DIMENSION});
        """)
        
        # 2. answers (답변 벡터)
        # [수정] ADD IF NOT EXISTS 대신 DROP + ADD로 변경
        cur.execute(f"""
            ALTER TABLE {ANSWERS_TABLE} 
            DROP COLUMN IF EXISTS a_vector;
        """)
        cur.execute(f"""
            ALTER TABLE {ANSWERS_TABLE} 
            ADD COLUMN a_vector VECTOR({EMBEDDING_DIMENSION});
        """)
        
        # 3. respondents (프로필 벡터)
        # (이 로직은 이미 DROP + ADD로 올바르게 되어 있었음)
        cur.execute(f"""
            ALTER TABLE {RESPONDENTS_TABLE} 
            DROP COLUMN IF EXISTS profile_vector;
        """)
        cur.execute(f"""
            ALTER TABLE {RESPONDENTS_TABLE} 
            ADD COLUMN profile_vector VECTOR({EMBEDDING_DIMENSION});
        """)
        
        conn.commit()
        print(">>> [Phase 2] 모든 벡터 컬럼 셋업 완료.")
        return True
    except Exception as e:
        print(f"XXX [Phase 2] 벡터 컬럼 셋업 중 오류 발생: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

# --- 3. [신규] Codebook 임베딩 함수 ---
def embed_codebooks(conn, model):
    """codebooks 테이블의 모든 질문(q_title)을 임베딩합니다."""
    print("\n>>> [Phase 3] Codebook (질문) 임베딩 시작...")
    cur = conn.cursor()
    try:
        # q_vector가 NULL인 (아직 임베딩되지 않은) 질문들을 가져옵니다.
        cur.execute(f"""
            SELECT codebook_id, codebook_data ->> 'q_title' AS q_title
            FROM {CODEBOOKS_TABLE}
            WHERE (codebook_data ->> 'q_title') IS NOT NULL
              AND q_vector IS NULL;
        """)
        rows = cur.fetchall()
        
        if not rows:
            print("  [Info] 새로 임베딩할 질문이 없습니다.")
            return

        print(f"  [Info] 총 {len(rows)}개의 신규 질문을 임베딩합니다.")
        
        texts_to_embed = [row[1] for row in rows]
        ids_to_update = [row[0] for row in rows]
        
        # 모델을 통해 텍스트 리스트를 벡터 리스트로 변환
        vectors = model.get_embeddings(texts_to_embed)
        
        # [수정] psycopg2가 numpy array를 인식하도록 .tolist() 호출
        update_data = [(v.tolist(), id_val) for v, id_val in zip(vectors, ids_to_update)]

        # execute_values로 DB에 일괄 업데이트
        update_query = f"""
            UPDATE {CODEBOOKS_TABLE} SET q_vector = data.q_vector
            FROM (VALUES %s) AS data (q_vector, codebook_id)
            WHERE {CODEBOOKS_TABLE}.codebook_id = data.codebook_id;
        """
        execute_values(cur, update_query, update_data, page_size=BATCH_SIZE)
        conn.commit()
        
        print(f"  [Success] {len(rows)}개의 질문 벡터(q_vector) 저장 완료.")

    except Exception as e:
        print(f"  XXX [Phase 3] Codebook 임베딩 중 오류 발생: {e}")
        conn.rollback()
    finally:
        cur.close()

# --- 4. [신규] Answers 임베딩 함수 (핵심 로직) ---
def embed_answers(conn, model):
    """
    answers 테이블의 답변을 임베딩합니다.
    - (요청사항 1) 객관식: 코드북의 '보기 텍스트' (예: '미혼')
    - (요청사항 1) 주관식: 'answer_value' 원본 텍스트 (예: 'K5', '너무 비싸요')
    """
    print("\n>>> [Phase 4] Answers (답변) 임베딩 시작...")
    cur = conn.cursor()
    try:
        # a_vector가 NULL인 (임베딩 안 된) 답변들을 코드북 정보와 함께 가져옵니다.
        # [최적화] LIMIT...OFFSET을 사용하여 대용량 데이터를 청크(chunk) 단위로 처리
        
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
            """ # OFFSET을 사용하지 않고, 처리된 항목(NULL이 아님)을 제외하며 반복
            
            cur.execute(query)
            rows = cur.fetchall()
            
            if not rows:
                print("  [Info] 새로 임베딩할 답변이 더 이상 없습니다.")
                break # 루프 종료

            print(f"  [Info] {len(rows)}개의 신규 답변을 처리합니다. 임베딩할 텍스트 추출 중...")

            tasks = [] # (text_to_embed, answer_id)
            ids_to_mark_null = [] # 임베딩할 텍스트가 없는 답변 ID (다시 조회되지 않도록)

            for row in rows:
                answer_id, answer_value, codebook_data = row
                
                if not answer_value or not codebook_data:
                    ids_to_mark_null.append((answer_id,))
                    continue

                choices = codebook_data.get('answers', [])
                text_to_embed = None

                # [핵심 로직 1] 객관식
                if choices:
                    for choice in choices:
                        if str(choice.get('qi_val')).strip() == str(answer_value).strip():
                            text_to_embed = str(choice.get('qi_title')).strip()
                            break
                
                # [핵심 로직 2 - Fallback] 주관식/기타
                if not text_to_embed:
                    # answer_value가 단순 숫자가 아닌 '텍스트'일 경우에만 임베딩
                    if not str(answer_value).replace('.', '', 1).isdigit():
                        text_to_embed = str(answer_value).strip()

                if text_to_embed:
                    tasks.append((text_to_embed, answer_id))
                else:
                    # 임베딩할 가치가 없는 답변 (예: 단순 숫자 '1')도 NULL 처리 대상
                    ids_to_mark_null.append((answer_id,))
            
            if not tasks and not ids_to_mark_null:
                continue # 처리할 작업이 없음
                
            print(f"  [Info] {len(rows)}개 중 {len(tasks)}개의 텍스트 답변 임베딩 / {len(ids_to_mark_null)}개는 NULL로 표시.")

            # --- 일괄 임베딩 및 DB 업데이트 ---
            if tasks:
                texts_to_embed = [task[0] for task in tasks]
                ids_to_update = [task[1] for task in tasks]
                vectors = model.get_embeddings(texts_to_embed)
                
                # [수정] .tolist() 호출
                update_data = [(v.tolist(), id_val) for v, id_val in zip(vectors, ids_to_update)]

                update_query = f"""
                    UPDATE {ANSWERS_TABLE} SET a_vector = data.a_vector
                    FROM (VALUES %s) AS data (a_vector, answer_id)
                    WHERE {ANSWERS_TABLE}.answer_id = data.answer_id;
                """
                execute_values(cur, update_query, update_data, page_size=BATCH_SIZE)
            
            # [신규] 임베딩할 수 없는 답변들(ids_to_mark_null) 처리
            # a_vector에 (0,0,...) 같은 '제로 벡터'를 넣어, 다음 조회에서 제외되도록 함
            if ids_to_mark_null:
                zero_vector = [0.0] * EMBEDDING_DIMENSION
                update_data_null = [(zero_vector, id_val[0]) for id_val in ids_to_mark_null]
                
                update_query_null = f"""
                    UPDATE {ANSWERS_TABLE} SET a_vector = data.a_vector
                    FROM (VALUES %s) AS data (a_vector, answer_id)
                    WHERE {ANSWERS_TABLE}.answer_id = data.answer_id;
                """
                execute_values(cur, update_query_null, update_data_null, page_size=BATCH_SIZE)

            conn.commit() # 이번 배치 작업 커밋
            total_processed += len(rows)
        
        print(f"  [Success] 총 {total_processed}개의 답변 벡터(a_vector) 처리 완료.")

    except Exception as e:
        print(f"  XXX [Phase 4] Answers 임베딩 중 오류 발생: {e}")
        conn.rollback()
    finally:
        cur.close()

# --- 6. 메인 실행 파이프라인 ---
def main():
    print("===== 임베딩 파이프라인 시작 =====")
    
    try:
        # [수정] KURE 모델 초기화
        model = KUREEmbeddingModel(dimension=EMBEDDING_DIMENSION)
    except Exception as e:
        print("XXX 모델 초기화 실패. 스크립트를 종료합니다.")
        return

    db_conn = connect_to_db() # 1. DB 연결
    if db_conn:
        try:
            # 2. DB 스키마(벡터 컬럼) 설정
            if not setup_vector_columns(db_conn):
                print("오류: 마스터 테이블 벡터 컬럼 생성에 실패하여 ETL을 중단합니다.")
                db_conn.close()
                return

            # 3. Codebook (질문) 임베딩 실행
            embed_codebooks(db_conn, model)
            
            # 4. Answers (답변) 임베딩 실행 (핵심 로직)
            embed_answers(db_conn, model)
            
            

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

