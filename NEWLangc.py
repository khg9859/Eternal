import os
import sys
import json
from typing import List, Dict, Any, Tuple, Literal, Optional
from datetime import datetime

from dotenv import load_dotenv
# OpenAI 클라이언트만 사용
from openai import OpenAI
import numpy as np 

# --- RAG CORE COMPONENTS ---
from langchain_core.runnables import RunnablePassthrough 
from langchain_core.prompts import PromptTemplate 
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# --- LLM, EMBEDDINGS, VECTOR STORE ---
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector 


# 환경 변수 로드
load_dotenv() 

# ====================================================================
# 1. 설정 및 모델 정의 (Settings & Definitions)
# ====================================================================

KURE_MODEL_NAME = "nlpai-lab/KURE-v1" 
CONNECTION_STRING = os.getenv("PG_CONNECTION_STRING")
COLLECTION_NAME = "panel_data_kure_v1" 

# --- 모델 변경 및 역할 정의 (GPT-5로 통일) ---
OPENAI_GPT5_MODEL = "gpt-5-standard"             # Reranker, 프로필 추출, 라우팅, CHAT 답변 모두 담당
ANTHROPIC_DECODER_MODEL = "claude-3-opus-20240229" # 최종 답변 생성 (Opus 유지)
RETRIEVAL_K = 20 
FINAL_K = 3

# --- 메모리 저장소 (RAM) 및 문서 재참조 정책 설정 ---
store = {} 
STORED_DOC_LIMIT = FINAL_K # 재참조 정책: 저장할 문서 수를 FINAL_K(3개)로 제한합니다.

# --- Pydantic 모델 정의 (라우팅 결정용) ---
class RouteDecision(BaseModel):
    """사용자 질문을 분석하여 실행 경로를 결정합니다."""
    route: Literal["RAG", "CHAT", "CACHE"] = Field(
        description="RAG: 새로운 데이터 검색 및 Opus 추론이 필요한 경우. CHAT: 일반 대화/인사말. CACHE: 이전 RAG 결과 재활용 가능 (시맨틱 캐싱)."
    )
    cache_answer: Optional[str] = Field(
        description="route가 CHAT일 경우, 사용자에게 바로 전달할 답변 텍스트를 여기에 생성합니다. CACHE/RAG일 경우 null."
    )
    is_similar_to_previous: bool = Field(
        description="현재 질문이 바로 이전 턴의 질문과 동일하거나 매우 유사한 내용인지 판단합니다. (재활용 판단 보조용)"
    )

# ====================================================================
# 1.1. 세션 메모리 관리 함수 (문서 저장을 위한 구조 변경)
# ====================================================================

def get_session_data(session_id: str) -> Dict[str, Any]:
    """Retrieves or initializes the full session data dictionary."""
    if session_id not in store:
        store[session_id] = {
            "history": ChatMessageHistory(),
            "last_rag_docs": [] # [Metadata, Content] list for last successful RAG
        }
    return store[session_id]

def get_session_history(session_id: str) -> ChatMessageHistory:
    """Returns the chat history object."""
    return get_session_data(session_id)["history"]

def set_last_rag_docs(session_id: str, docs: List[Any]):
    """Stores the necessary metadata/content of the last successful RAG documents (재참조 정책 적용)."""
    formatted_docs = []
    # 정책: 최종 K개 문서만 저장
    for doc in docs[:STORED_DOC_LIMIT]: 
        # LangChain Document 객체 대신 필요한 텍스트와 메타데이터만 저장
        formatted_docs.append({
            "page_content": getattr(doc, 'page_content', ''),
            "metadata": getattr(doc, 'metadata', {})
        })
    get_session_data(session_id)["last_rag_docs"] = formatted_docs
    print(f"[INFO] 세션 {session_id}에 최종 문서 {len(formatted_docs)}개 저장 완료. (재참조 정책: {STORED_DOC_LIMIT}개)")

def get_last_rag_docs(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves the stored documents."""
    return get_session_data(session_id)["last_rag_docs"]

def get_llm():
    """RAG Decoder: Claude Opus LLM을 정의합니다."""
    return ChatAnthropic(model=ANTHROPIC_DECODER_MODEL, temperature=0.1)

# GPT-5 클라이언트 정의 (라우팅, 추출, 재순위 모두 담당)
openai_client = ChatOpenAI(model=OPENAI_GPT5_MODEL, temperature=0.0)

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
    """저장된 문서 객체의 page_content만 추출하여 문자열로 포맷합니다."""
    # Docs can be LangChain Document objects or Dicts (for stored docs)
    return "\n\n".join([doc.get('page_content', doc.page_content) for doc in docs])

# ... (get_kure_embedding 생략) ...

# ====================================================================
# 2. RAG 체인 객체 구축 (Retriever 및 Reranker 로직 유지)
# ====================================================================

# ... (extract_profile_query, rerank_with_openai 함수 생략) ...

# 2.2. 사용자 정의 Retriever 함수 (Full RAG 검색 시뮬레이션)
def get_multistage_retriever(query: str):
    """
    RAG 검색의 핵심 단계 (GPT-5 추출/재순위 포함)를 시뮬레이션하고,
    저장을 위해 LangChain Document 객체 리스트를 반환합니다.
    """
    print(f"\n[DEBUG] Full RAG 검색 프로세스 실행. 쿼리: {query}")
    # Simulating the final 3 high-quality documents after reranking
    class DummyDoc:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata
        
    # 실제로는 DB/GPT-5 호출 결과 (FINAL_K=3)
    return [
        DummyDoc(f"[Document 1: ID Q_123] {query}에 대한 핵심 데이터입니다. (Rank: 1)", {"source": "DB_A", "rank": 1}),
        DummyDoc(f"[Document 2: ID R_456] {query}와 관련된 보조 데이터입니다. (Rank: 2)", {"source": "DB_B", "rank": 2}),
        DummyDoc(f"[Document 3: ID S_789] {query}와 관련된 통계 요약입니다. (Rank: 3)", {"source": "DB_C", "rank": 3}),
    ][:FINAL_K]


# ... (2.3. RAG 체인 객체 구축 부분 생략) ...

# 2.4. core_rag_chain 정의 (Opus Decoder 사용)
core_rag_chain = (
    {
        "context": lambda x: format_docs(get_multistage_retriever(x['question'])),
        "question": lambda x: x['question'],
        "history": lambda x: x['history']
    }
    | RAG_PROMPT
    | get_llm() # Claude Opus
    | StrOutputParser()
)

# 2.5. final_rag_chain 정의 (대화형 검색의 최종 체인)
final_rag_chain = RunnableWithMessageHistory(
    core_rag_chain,
    get_session_history, 
    input_messages_key="question",
    history_messages_key="history",
)

# 2.6. Hybrid Cache Chain 정의 (Opus Decoder 사용, Context를 외부에서 주입)
hybrid_cache_chain = (
    {
        "context": RunnablePassthrough(), # Context는 handle_user_query에서 직접 주입됨
        "question": lambda x: x['question'],
        "history": lambda x: x['history']
    }
    | RAG_PROMPT
    | get_llm() # Claude Opus
    | StrOutputParser()
)


# ====================================================================
# 3. 비용 최적화 및 간편 검색/대화형 검색 실행 함수 (라우팅 LLM)
# ====================================================================

# ... (route_query_with_llm 함수는 그대로 유지) ...


def handle_user_query(query: str, session_id: str, mode: str = "conv") -> str:
    """
    서버의 요청을 받아 RAG 체인을 실행하고 답변을 반환하는 메인 실행 함수입니다.
    (라우팅 LLM 및 CHAT 답변 생성에 GPT-5 Standard 사용)
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] --- Query: {query} ---")
    config = {"configurable": {"session_id": session_id}}
    
    try:
        # 1. 라우팅 LLM을 통한 경로 결정 (GPT-5 Standard 호출)
        chat_history = get_session_history(session_id).messages
        route_decision = route_query_with_llm(query, chat_history)
        
        print(f"[DEBUG] 라우팅 결정: {route_decision.route}, 유사성: {route_decision.is_similar_to_previous}")
        
        # --- CACHE / CHAT 경로 (우회 및 GPT-5/Opus 사용) ---
        if route_decision.route == "CHAT":
            # (CHAT 로직 유지 - GPT-5로 답변 생성)
            print(f"[INFO] 경로: CHAT. RAG/Opus 호출 회피. (LLM: {OPENAI_GPT5_MODEL} 사용)")
            final_answer = route_decision.cache_answer if route_decision.cache_answer else "죄송하지만, 답변을 생성하지 못했습니다."
            
            # 대화 기록 수동 업데이트
            get_session_history(session_id).add_user_message(query)
            get_session_history(session_id).add_ai_message(final_answer)
            return final_answer
        
        elif route_decision.route == "CACHE":
            # --- (수정) HYBRID CACHE 경로: 문서 재참조 및 Opus 재활용 ---
            stored_docs = get_last_rag_docs(session_id)
            if not stored_docs:
                # 저장된 문서가 없으면 RAG로 폴백
                print("[WARN] CACHE 경로 판단, 그러나 저장된 문서 없음. RAG 경로로 폴백 처리.")
                route_decision.route = "RAG"
            else:
                print(f"[INFO] 경로: HYBRID CACHE. GPT-5/DB 검색 회피. (LLM: {ANTHROPIC_DECODER_MODEL} 재활용)")
                
                # Context 포맷팅 (저장된 문서의 page_content만 추출하여 Claude Opus에 전달)
                context_str = format_docs(stored_docs)
                
                # Hybrid Cache Chain 호출 (Opus 사용, Context는 메모리에서 재참조)
                hybrid_response = hybrid_cache_chain.invoke({
                    "context": context_str,
                    "question": query,
                    "history": "\n".join([f"- {msg.type}: {msg.content}" for msg in chat_history])
                })
                
                # 대화 기록 수동 업데이트
                get_session_history(session_id).add_user_message(query)
                get_session_history(session_id).add_ai_message(hybrid_response)
                
                return hybrid_response
        
        # 2. RAG 실행 (Full Cost: GPT-5 + Claude Opus 사용)
        if route_decision.route == "RAG":
            print(f"[INFO] 경로: RAG. Full RAG Chain 실행. (LLM: {OPENAI_GPT5_MODEL} / {ANTHROPIC_DECODER_MODEL} 사용)")
            
            # Full RAG Chain 실행 (내부적으로 get_multistage_retriever 호출)
            response = final_rag_chain.invoke({"question": query}, config=config)
            
            # --- (수정) Full RAG 실행 후 문서 저장 (재참조 정책 반영) ---
            # NOTE: 실제 코드에서는 체인 실행 중 사용된 문서를 추출해야 함. 
            # 여기서는 시뮬레이션을 위해 get_multistage_retriever를 다시 호출하여 최종 문서를 가정합니다.
            final_docs_for_storage = get_multistage_retriever(query) 
            if final_docs_for_storage:
                 set_last_rag_docs(session_id, final_docs_for_storage)

            return response
        
        return "알 수 없는 경로 오류가 발생했습니다."

    except Exception as e:
        print(f"Execution Error in handle_user_query: {e}")
        return f"[오류] 서버 실행 오류: {e}"

# ***************************************************************
# (필수) 기존 main.py 파일에서 호출하는 인터페이스 유지
# ***************************************************************

def rag_search_with_sources(query: str, session_id: str, mode: str = "conv") -> dict:
    """
    원래 main.py가 호출하던 함수. handle_user_query를 사용하여 답변과 소스를 반환.
    """
    answer = handle_user_query(query, session_id, mode)

    # Hybrid Cache 경로일 경우, 메모리에서 소스를 불러와 반환합니다.
    stored_docs = get_last_rag_docs(session_id)
    
    # RAG나 CACHE 경로일 경우 소스를 반환
    if stored_docs and "죄송하지만" not in answer:
        sources = stored_docs
    else:
        sources = []
    
    # JSON으로 직렬화 가능한 형태로 변환
    formatted_sources = []
    for doc in sources:
        formatted_sources.append({
            "page_content": doc.get('page_content', ''),
            "metadata": doc.get('metadata', {})
        })

    return {"answer": answer, "sources": formatted_sources, "session_id": session_id}


# ====================================================================
# 4. (옵션) 테스트 코드
# ====================================================================
if __name__ == "__main__":
    
    q_chat = "안녕하세요! 오늘 날씨는 어떤가요?"
    q_rag_1 = "서울 20대 남자 100명에 대한 소비 동향을 요약해줘."
    q_rag_cache = "아까 말한 남자들의 점심 메뉴는 뭐야? 아침 식사 습관과 비교해서 알려줘."

    TEST_SESSION_ID = "test_hybrid_cache_session" 
    
    # 세션 데이터 초기화 (테스트를 위해)
    if TEST_SESSION_ID in store: del store[TEST_SESSION_ID]

    print("--- 1. Q_CHAT 테스트 실행 (GPT-5 Standard 단순 답변) ---")
    answer_chat = handle_user_query(q_chat, TEST_SESSION_ID, mode="conv")
    print(f"답변: {answer_chat}")
    
    print("\n--- 2. Q_RAG_1 테스트 실행 (Full RAG Chain 실행 및 문서 저장) ---")
    answer_rag_1 = handle_user_query(q_rag_1, TEST_SESSION_ID, mode="conv")
    print(f"답변: {answer_rag_1}")
    
    print("\n--- 3. Q_RAG_CACHE 테스트 실행 (HYBRID CACHE 실행: 문서 재참조 및 Opus 재활용) ---")
    answer_rag_cache = handle_user_query(q_rag_cache, TEST_SESSION_ID, mode="conv")
    print(f"답변: {answer_rag_cache}")