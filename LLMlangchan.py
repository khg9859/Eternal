import os
import sys
import json
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
from openai import OpenAI
import numpy as np # 벡터 재정렬 및 비교에 필요

# --- RAG CORE COMPONENTS ---
from langchain_core.runnables import RunnablePassthrough 
from langchain_core.prompts import PromptTemplate 
from langchain_core.output_parsers import StrOutputParser 
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# --- LLM, EMBEDDINGS, VECTOR STORE ---
from langchain_anthropic import ChatAnthropic # Claude LLM (Decoder)
from langchain_openai import ChatOpenAI # ✨ OpenAI Tool Call 및 Reranker에 사용
from langchain_community.embeddings import HuggingFaceEmbeddings # KURE-v1 (Encoder)
from langchain_community.vectorstores.pgvector import PGVector 


# 환경 변수 로드
load_dotenv() 

# ====================================================================
# 1. 설정 및 모델 정의 (Settings & Definitions)
# ====================================================================

KURE_MODEL_NAME = "nlpai-lab/KURE-v1" 
CONNECTION_STRING = os.getenv("PG_CONNECTION_STRING")
COLLECTION_NAME = "panel_data_kure_v1" 

# --- 재순위 지정 설정 ---
OPENAI_RERANKER_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini") # 재순위 지정에 사용할 OpenAI 모델
RETRIEVAL_K = 20 # 1차 검색(KURE)에서 가져올 넓은 후보군 수
FINAL_K = 3      # 재순위 지정 후 최종적으로 사용할 문서 수

# --- 메모리 저장소 (RAM) ---
store = {} 

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def get_kure_embedding():
    """RAG Encoder: KURE-v1 모델을 로드하여 임베딩 함수를 반환합니다."""
    return HuggingFaceEmbeddings(
        model_name=KURE_MODEL_NAME,
        model_kwargs={'device': 'cpu'} 
    )

def get_llm():
    """RAG Decoder: Claude LLM을 정의합니다."""
    # Claude가 최종 답변을 생성하는 Decoder 역할
    return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0.1)


# --- LLM 디자이너가 최종 결정한 프롬프트 템플릿 ---
RAG_PROMPT = PromptTemplate(
    input_variables=["question", "context", "history"], 
    template="""
        Human: 
        당신은 전문 AI 데이터 비서입니다. 이전 대화 내역과 아래 지시사항을 참고하여 답변하세요.

        [이전 대화 기록]:
        {history} 
        
        아래 지시사항을 따르세요:
        1. 질문에 오탈자가 있다면 표준어로 교정하고, 모호하면 구체적인 키워드로 질문을 재작성 후 검색 결과에 적용.
        2. '참고 문서'에 없는 정보는 절대 사용 금지.
        3. 질문에 대한 핵심 정보만 요약하여, 서론/결론 없이 바로 시작.
        4. 검색 결과가 부족하면 "죄송하지만, 검색된 문서로는 질문에 대한 충분한 정보를 찾을 수 없습니다."라고 응답.

        [질문]:
        {question}
        
        [참고 문서 - Vector DB 검색 결과]:
        {context}
        
        Assistant:
    """
)

def format_docs(docs):
    """검색된 Document 객체의 page_content만 추출하여 문자열로 포맷합니다."""
    return "\n\n".join([doc.page_content for doc in docs])


# ====================================================================
# 2. RAG 체인 객체 구축 (KURE-v1 검색 + OpenAI 재순위 지정 통합)
# ====================================================================

# 툴콜에 필요한 OpenAI 클라이언트 (재순위 지정에도 사용)
openai_client = ChatOpenAI(model=OPENAI_RERANKER_MODEL, temperature=0.0)

# 2.1. 재순위 지정(Re-ranking) 함수 정의
def rerank_with_openai(query: str, retrieved_docs: List[Any], final_k: int = FINAL_K) -> List[Any]:
    """
    KURE-v1이 검색한 Top-N 문서를 OpenAI의 추론 능력을 사용해 최종 Top-K로 재정렬합니다.
    """
    if not retrieved_docs:
        return []

    # 1. 재순위 지정을 위한 컨텍스트 및 ID 목록 생성
    ranked_context = "\n\n--- 문서 목록 ---\n\n"
    id_map = {}
    
    # Simple RAG: Document 객체를 Dictionary로 변환하여 사용해야 함 (PageContent와 Metadata 사용)
    for i, doc in enumerate(retrieved_docs):
        doc_id = f"DOC_{i:03d}"
        id_map[doc_id] = doc # 원본 Document 객체 저장
        
        # 문서 내용 추출 및 포맷팅
        page_content = doc.page_content.replace('\n', ' ')[:150] # 150자만 요약
        ranked_context += f"[[{doc_id}]] - 내용 요약: {page_content}...\n"
    
    # 2. LLM에게 재순위 지정 요청 프롬프트 작성
    rerank_prompt = f"""
    아래 '질문'과 '문서 목록'을 분석하여, 질문에 답변하는 데 가장 관련성이 높은 {final_k}개의 문서 ID를 **높은 순서대로만** 골라 JSON 배열 형태로 반환하세요.
    반드시 문서 목록에 있는 ID만 사용하며, 다른 설명이나 텍스트는 일절 포함하지 마십시오.
    출력 형식: {{"ids": ["DOC_001", "DOC_002", ...]}}

    [질문]
    {query}

    [문서 목록]
    {ranked_context}
    """
    
    # 3. OpenAI 호출 및 결과 파싱
    try:
        response = openai_client.invoke(
            rerank_prompt,
            response_format={"type": "json_object"} # JSON 출력을 강제
        )
        
        content = response.content.strip()
        
        # '{"ids": [...]}' 형태의 JSON 파싱
        reranked_data = json.loads(content)
        reranked_ids = reranked_data.get("ids", []) 

        # 재정렬된 ID 순서에 따라 최종 결과 목록 생성
        final_list = [id_map[doc_id] for doc_id in reranked_ids if doc_id in id_map]
                
        # 최종 K개만 반환
        return final_list[:final_k]
    
    except Exception as e:
        print(f"[RERANK] OpenAI API 호출 또는 파싱 오류: {e}")
        # API 오류 시, 1차 검색 결과를 그대로 반환 (안전 폴백)
        return retrieved_docs[:final_k]


# 2.2. 사용자 정의 Retriever 함수 (1차 KURE 검색 후 OpenAI 재순위 지정)
def get_hybrid_retriever(query: str):
    """KURE 검색 후 OpenAI 재순위 지정"""
    docs_to_rerank = retriever.invoke(query, search_kwargs={"k": RETRIEVAL_K})
    final_docs = rerank_with_openai(query, docs_to_rerank, final_k=FINAL_K)  # ← 함수명 통일
    return final_docs


# 2.3. RAG 체인 객체 구축 (try/except 블록 유지)
try:
    if not CONNECTION_STRING:
        raise RuntimeError("PG_CONNECTION_STRING 환경 변수가 설정되지 않았습니다.")

    embedding_function = get_kure_embedding()
    
    vectorstore = PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        embedding_function=embedding_function
    )
    # 기존 retriever 객체는 1차 검색에만 사용됨
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K}) 

except RuntimeError as e:
    print(f"XXX PGVector 설정 오류: {e}")
    sys.exit(1)
except Exception as e:
    print(f"XXX PGVector 접속 중 심각한 오류 발생: {e}")
    sys.exit(1)


# 2.4. core_rag_chain 정의 (메모리 없는 단발성 RAG)
core_rag_chain = (
    {
        # 최종 문서를 문자열 컨텍스트로 포맷해서 프롬프트에 투입
        "context": lambda x: format_docs(get_hybrid_retriever(x['question'])),
        "question": lambda x: x['question'],
        "history": lambda x: x['history']
    }
    | RAG_PROMPT
    | get_llm()
    | StrOutputParser()
)

def rag_answer(query: str, session_id: str, mode: str = "conv") -> str:
    """외부(백엔드)에서 바로 호출할 간편 함수"""
    config = {"configurable": {"session_id": session_id}}
    try:
        if mode == "simple":
            return core_rag_chain.invoke({"question": query, "history": ""})
        else:
            return final_rag_chain.invoke({"question": query}, config=config)
    except Exception as e:
        return f"[오류] 서버 실행 오류: {e}"

# 2.5. final_rag_chain 정의 (대화형 검색의 최종 체인)
final_rag_chain = RunnableWithMessageHistory(
    core_rag_chain,
    get_session_history, 
    input_messages_key="question",
    history_messages_key="history",
)


# ====================================================================
# 3. 간편 검색/대화형 검색 실행 함수 (서버 통합 지점)
# ====================================================================

def handle_user_query(query: str, session_id: str, mode: str = "conv") -> str:
    """
    서버의 요청을 받아 RAG 체인을 실행하고 답변을 반환하는 메인 실행 함수입니다.
    """
    
    config = {"configurable": {"session_id": session_id}}
    
    try:
        if mode == "simple":
            # 간편 검색: 메모리 없는 core_rag_chain 사용
            response = core_rag_chain.invoke({"question": query, "history": ""})
        
        else: # mode == "conv" (대화형 검색)
            response = final_rag_chain.invoke({"question": query}, config=config)
        
        return response

    except Exception as e:
        print(f"Execution Error in handle_user_query: {e}")
        return f"[오류] 서버 실행 오류: {e}"


# ====================================================================
# 4. (옵션) 테스트 코드
# ====================================================================
if __name__ == "__main__":
    
    # ... (테스트 쿼리 및 실행 로직 유지) ...
    q1 = "서울 20대 남자 100명에 대한 정보를 요약해줘."
    q2 = "경기 30~40대 남자 술을 먹은 사람 50명에 대한 정보를 요약해줘."
    q3 = "서울, 경기 OTT 이용하는 젊은층 30명에 대한 정보를 요약해줘."

    TEST_SESSION_ID = "test_session_multi_query" 
    
    print("--- 1. Q1 테스트 실행 (단발성 simple) ---")
    answer_q1 = handle_user_query(q1, TEST_SESSION_ID, mode="simple")
    print(f"답변: {answer_q1}")

    print("\n--- 2. Q2 테스트 실행 (대화형 시작) ---")
    answer_q2 = handle_user_query(q2, TEST_SESSION_ID, mode="conv") 
    print(f"답변: {answer_q2}")

    print("\n--- 3. Q3 테스트 실행 (대화형 후속 질문 - Q2 맥락 기억) ---")
    answer_q3 = handle_user_query(q3, TEST_SESSION_ID, mode="conv")
    print(f"답변: {answer_q3}")