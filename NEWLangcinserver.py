import os
import sys
import json
from typing import List, Dict, Any, Tuple, Literal, Optional
from datetime import datetime
from collections import deque # deque는 사용되지 않으나, 이전 CACHE 로직 흔적으로 유지 (사용자 코드를 따름)

from dotenv import load_dotenv, find_dotenv # 환경 변수 로드 추가
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


# 환경 변수 로드 (main.py 외 단독 실행 시를 대비해 여기서도 로드)
load_dotenv(find_dotenv()) 

# ====================================================================
# 1. 설정 및 모델 정의 (Settings & Definitions)
# ====================================================================

KURE_MODEL_NAME = "nlpai-lab/KURE-v1" 
# --- (수정) PGVector 연결 문자열 구성 (환경 변수 사용) ---
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# PGVector 연결 문자열 (DB 보안을 위해 환경 변수 사용)
CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# ------------------------------------------------------------------

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
        page_content = getattr(doc, 'page_content', doc.get('page_content', ''))
        metadata = getattr(doc, 'metadata', doc.get('metadata', {}))
        
        formatted_docs.append({
            "page_content": page_content,
            "metadata": metadata
        })
    get_session_data(session_id)["last_rag_docs"] = formatted_docs
    print(f"[INFO] 세션 {session_id}에 최종 문서 {len(formatted_docs)}개 저장 완료. (재참조 정책: {STORED_DOC_LIMIT}개)")

def get_last_rag_docs(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves the stored documents."""
    return get_session_data(session_id)["last_rag_docs"]

def get_kure_embedding():
    """RAG Encoder: KURE-v1 모델을 로드하여 임베딩 함수를 반환합니다."""
    return HuggingFaceEmbeddings(
        model_name=KURE_MODEL_NAME,
        model_kwargs={'device': 'cpu'} 
    )

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
    return "\n\n".join([doc.get('page_content', getattr(doc, 'page_content', '')) for doc in docs])


# ====================================================================
# 2. RAG 체인 객체 구축 (Retriever 및 Reranker 로직 통합)
# ====================================================================

# 2.0. 프로필 추출 (GPT-5 사용)
def extract_profile_query(query: str) -> str:
    """LLM을 사용해 전체 질문에서 프로필 관련 키워드만 추출합니다. (GPT-5 Standard 사용)"""
    
    profile_extraction_prompt = f"""사용자의 전체 질문에서 '사람'의 특징을 설명하는 핵심 키워드만 추출하여 간결한 구(phrase)로 만들어주세요. 다른 설명은 절대 추가하지 마세요. 질문: "{query}" 출력:"""

    try:
        response = openai_client.invoke(profile_extraction_prompt)
        return response.content.strip().replace('"', '')
    except Exception as e:
        print(f"[WARN] 프로필 쿼리 추출 실패: {e}.")
        return query 

# 2.1. 재순위 지정(Re-ranking) 함수 정의 (GPT-5 Standard 사용)
def rerank_with_openai(query: str, retrieved_docs: List[Any], final_k: int = FINAL_K) -> List[Any]:
    """
    KURE-v1이 검색한 Top-N 문서를 GPT-5의 추론 능력을 사용해 최종 Top-K로 재정렬합니다.
    """
    if not retrieved_docs:
        return []

    # 1. 재순위 지정을 위한 컨텍스트 및 ID 목록 생성 (로직 생략)
    ranked_context = "\n\n--- 문서 목록 ---\n\n"
    id_map = {}
    
    for i, doc in enumerate(retrieved_docs):
        doc_id = f"DOC_{i:03d}"
        id_map[doc_id] = doc 
        
        page_content = getattr(doc, 'page_content', doc.get('page_content', ''))
        ranked_context += f"[[{doc_id}]] - 내용 요약: {page_content[:150].replace('\n', ' ')}...\n"
    
    # 2. LLM에게 재순위 지정 요청 프롬프트 작성 (GPT-5 추론)
    rerank_prompt = f"""
    아래 '질문'과 '문서 목록'을 분석하여, 질문에 답변하는 데 가장 관련성이 높은 {final_k}개의 문서 ID를 **높은 순서대로만** 골라 JSON 배열 형태로 반환하세요.
    반드시 문서 목록에 있는 ID만 사용하며, 다른 설명이나 텍스트는 일절 포함하지 마십시오.
    출력 형식: {{"ids": ["DOC_001", "DOC_002", ...]}}

    [질문]
    {query}

    [문서 목록]
    {ranked_context}
    """
    
    # 3. GPT-5 호출 및 결과 파싱
    try:
        response = openai_client.invoke(
            rerank_prompt,
            response_format={"type": "json_object"}
        )
        
        reranked_data = json.loads(response.content.strip())
        reranked_ids = reranked_data.get("ids", []) 

        # 재정렬된 ID 순서에 따라 최종 결과 목록 생성
        final_list = [id_map[doc_id] for doc_id in reranked_ids if doc_id in id_map]
                
        return final_list[:final_k]
    
    except Exception as e:
        print(f"[RERANK] GPT-5 API 호출 또는 파싱 오류: {e}. 초기 {final_k}개 문서를 폴백으로 사용합니다.")
        return retrieved_docs[:final_k]


# 2.2. 사용자 정의 Retriever 함수 (0->1->2->3 Stage)
def get_multistage_retriever(query: str):
    """
    (0)프로필추출 -> (1)profile_vector -> (2)q_vector -> (3)a_vector를 모두 사용하는 최종 Retriever (PGVector 사용)
    """
    # NOTE: 이 함수는 RAG 경로일 때만 호출되므로, 비용 효율적임
    print(f"\n[DEBUG] Full RAG 검색 프로세스 시작. 원본 쿼리: {query}")

    # 0단계: 사용자 질문에서 프로필 검색어 추출 (GPT-5 Standard 호출)
    profile_query = extract_profile_query(query)
    print(f"[DEBUG] 0단계: 프로필 검색어 추출 완료: '{profile_query}'")

    # 1단계: profile_vector로 관련성 높은 응답자 후보군(mb_sn) 추출 (PGVector 사용)
    candidate_docs = profile_retriever.invoke(profile_query) 
    candidate_mb_sn_set = set([doc.metadata.get('mb_sn') for doc in candidate_docs if doc.metadata.get('mb_sn')])
    
    if not candidate_mb_sn_set:
        print("[DEBUG] 1단계: 관련 응답자 후보군을 찾지 못했습니다.")
        return []
    print(f"[DEBUG] 1단계: 응답자 후보군 {len(candidate_mb_sn_set)}명 발견.")

    # 2단계: q_vector로 가장 관련성 높은 설문 문항(question_id) 추출 (PGVector 사용)
    relevant_question_docs = q_retriever.invoke(query) 
    if not relevant_question_docs:
        print("[DEBUG] 2단계: 관련 설문 문항을 찾지 못했습니다.")
        return []
        
    question_id = relevant_question_docs[0].metadata.get('codebook_id')
    if not question_id:
        print("[DEBUG] 2단계: 설문 문항의 ID(codebook_id)를 찾지 못했습니다.")
        return []
    print(f"[DEBUG] 2단계: 관련 설문 문항 ID '{question_id}' 발견.")

    # 3단계: a_vector 검색 (question_id로 1차 필터링)
    # (PGVector/a_vectorstore 사용)
    a_retriever = a_vectorstore.as_retriever(
        search_kwargs={
            "k": RETRIEVAL_K, # 1차 검색으로 20개 문서 확보
            "filter": { "question_id": question_id }
        }
    )
    docs_for_manual_filter = a_retriever.invoke(query) 
    
    # 3.5단계: 응답자 후보군(mb_sn)으로 2차 수동 필터링
    final_docs_to_rerank = [doc for doc in docs_for_manual_filter 
                            if doc.metadata.get('mb_sn') in candidate_mb_sn_set]
    print(f"[DEBUG] 3단계: 최종 필터링 후 {len(final_docs_to_rerank)}개 문서 확보 (GPT-5 Reranking 대상).")

    # 4단계: GPT-5 Standard로 최종 FINAL_K(3개) 재정렬
    final_docs = rerank_with_openai(query, final_docs_to_rerank, final_k=FINAL_K)
    print(f"[DEBUG] 4단계: 재정렬 후 최종 {len(final_docs)}개 문서 반환.")
    
    return final_docs


# 2.3. RAG 체인 객체 구축 (Vector DB 연결)
try:
    if not CONNECTION_STRING:
        raise RuntimeError("DB 연결 정보(환경 변수)가 올바르지 않습니다.")

    embedding_function = HuggingFaceEmbeddings(
        model_name=KURE_MODEL_NAME,
        model_kwargs={'device': 'cpu'} 
    )
    
    # PGVector 인스턴스 생성 (실제 DB 연결)
    profile_vectorstore = PGVector(
        collection_name="respondents", connection_string=CONNECTION_STRING, embedding_function=embedding_function,
    )
    q_vectorstore = PGVector(
        collection_name="codebooks", connection_string=CONNECTION_STRING, embedding_function=embedding_function,
    )
    a_vectorstore = PGVector(
        collection_name="answers", connection_string=CONNECTION_STRING, embedding_function=embedding_function,
    )
    
    # Retriever 정의
    profile_retriever = profile_vectorstore.as_retriever(search_kwargs={"k": 50}) # 50명 후보군
    q_retriever = q_vectorstore.as_retriever(search_kwargs={"k": 1}) # 관련 질문 1개

except RuntimeError as e:
    print(f"XXX PGVector 설정 오류: {e}")
    sys.exit(1)
except Exception as e:
    print(f"XXX PGVector 접속 중 심각한 오류 발생: {e}")
    sys.exit(1)

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

# (라우팅 LLM GPT-5를 사용하는 RouteDecision 모델 정의)
def route_query_with_llm(current_query: str, chat_history: List[Any]) -> RouteDecision:
    """GPT-5 Standard를 사용하여 실행 경로를 결정합니다."""
    parser = PydanticOutputParser(pydantic_object=RouteDecision)
    
    history_summary = "\n".join([f"- {msg.type}: {msg.content}" for msg in chat_history])
    
    routing_prompt = f"""
    당신은 AI 라우팅 전문가입니다. 현재 질문과 이전 대화 기록을 분석하여, 실행 경로를 선택하고 JSON 형식으로 출력하세요.
    
    [이전 대화 기록 요약]:
    {history_summary}
    
    [현재 질문]: "{current_query}"
    
    경로 선택 기준:
    1. RAG: 새로운 데이터 검색 또는 복잡한 추론이 필요한 경우.
    2. CACHE: 현재 질문의 의미가 이전 턴에서 검색했던 자료군만으로 충분히 답변 가능할 경우. (이 경로를 선택했다면, cache_answer에 바로 쓸 답변을 생성하세요.)
    3. CHAT: 인사말, 일반 상식, 대화 유도 등 데이터 검색이 불필요한 경우. (이 경로를 선택했다면, cache_answer에 바로 쓸 답변을 생성하세요.)
    
    {parser.get_format_instructions()}
    """
    
    try:
        # GPT-5 Standard 호출
        response = openai_client.invoke(routing_prompt)
        return parser.parse(response.content)
    except Exception as e:
        print(f"[ERROR] 라우팅 LLM 오류: {e}. 안전하게 RAG 경로로 처리.")
        return RouteDecision(route="RAG", is_similar_to_previous=False)


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
            # --- HYBRID CACHE 경로: 문서 재참조 및 Opus 재활용 ---
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
                history_str = "\n".join([f"User: {m.content}" if m.type == 'human' else f"AI: {m.content}" for m in chat_history])
                
                # NOTE: core_rag_chain을 직접 호출하여 context와 history를 수동으로 제공
                hybrid_response = core_rag_chain.invoke({
                     "context": context_str,
                     "question": query,
                     "history": history_str
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
            
            # --- Full RAG 실행 후 문서 저장 (재참조 정책 반영) ---
            # NOTE: RAG 체인 실행 중 검색된 문서를 저장해야 하므로, get_multistage_retriever를 다시 호출하여 최종 문서를 가져옵니다.
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

    # RAG나 CACHE 경로일 경우 소스를 반환
    stored_docs = get_last_rag_docs(session_id)
    
    if stored_docs and "죄송하지만" not in answer and "[오류]" not in answer:
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
    
    print(f"\n[DEBUG] 저장된 문서 확인: {len(get_last_rag_docs(TEST_SESSION_ID))}개")
    
    print("\n--- 3. Q_RAG_CACHE 테스트 실행 (HYBRID CACHE 실행: 문서 재참조 및 Opus 재활용) ---")
    answer_rag_cache = handle_user_query(q_rag_cache, TEST_SESSION_ID, mode="conv")
    print(f"답변: {answer_rag_cache}")