# -*- coding: utf-8 -*-
"""
RAG 답변 요약기 (LLM Call #3: Synthesize)

[목적]
'rag_search_pipeline.py'가 반환한 RAG 검색 결과(JSON/dict)와
원본 사용자 질문을 gpt-4o 모델에 전달하여,
최종 사용자에게 보여줄 자연어 요약 답변을 생성합니다.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# --- 1. .env 파일 로드 및 OpenAI 클라이언트 초기화 ---
load_dotenv(find_dotenv())
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    print("XXX [오류] .env 파일에 'OPENAI_API_KEY'가 설정되지 않았습니다.")
    # 이 모듈이 다른 곳에서 import될 수 있으므로, exit() 대신 예외를 발생시킵니다.
    raise EnvironmentError("OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")

try:
    client = OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"XXX [오류] OpenAI 클라이언트 초기화 실패: {e}")
    client = None

# --- 2. LLM에게 전달할 시스템 프롬프트 정의 ---

SYSTEM_PROMPT = """
당신은 '설문조사 데이터 분석 AI 어시스턴트'입니다.
'원본 사용자 질문'과 'DB에서 검색된 관련 데이터(JSON)'가 제공됩니다.
당신의 임무는 이 두 가지 정보를 종합하여, 사용자의 질문에 대한
전문적이고 데이터에 기반한 '자연어 요약 답변'을 생성하는 것입니다.

[지침]
1.  **[매우 중요]** 'DB 검색 결과'는 '원본 사용자 질문'에 포함된 '필터 조건'(예: 30대, 남성, 서울)이 **'이미 적용된'** 결과입니다. 
    당신의 임무는 이 필터링된 데이터 내에서, 질문의 '주요 의도'(예: '전문직', '스트레스 해소법')에 해당하는 내용을 요약하는 것입니다.
    (예: "30대 남성"을 데이터 샘플에서 다시 찾으려 하지 마십시오.)

2.  **데이터 기반:** '제공된 데이터'의 명시된 내용만을 근거로 답변해야 합니다.
3.  **원본 질문 초점:** '원본 사용자 질문'의 의도에 정확히 맞는 답변을 하십시오.
4.  **[수정] 통계 및 비율 활용:**
    - `total_respondents_in_filter` (필터링된 총 응답자 수) 또는 `total_unique_answers_found` (v2의 고유 답변 수)를 기준으로 사용하십시오.
    - `grouped_answers_by_similarity` (v2)의 `respondent_count` (답변별 응답자 수)를 활용하십시오.
    - (예: "필터링된 461명(v1) 중 '전문직'은 1명입니다." 또는 "검색된 답변(v2) 중 '전문직'은 1명(X%)이었습니다.")
    - **수치와 비율(%)을 계산하여** 답변을 최대한 구체적이고 풍부하게 만드십시오.
    - 각 항목의 비율은 전체 응답 수 대비 백분율(%)로 계산하여 기재하십시오

5.  **합성(Synthesize):** 단순히 데이터를 나열하지 말고, "A 질문에 대해 B라고 답한 응답자는 C 질문에 대해 D라고 답하는 경향을 보입니다."처럼 데이터를 종합하고 통찰을 제공하십시오.
6.  **자신감 있는 답변:** 검색된 데이터가 질문에 답하기에 충분하다면, 자신감 있게 요약하십시오.
    (예: "30대 남성 중 전문직에 종사하는 응답자가 1명 발견되었습니다.")
    데이터가 부족할 경우에만 "DB에서 ... 다음과 같은 정보를 찾았습니다..."라고 한정하여 답변하십시오.
7.  **형식:** 최종 답변은 한국어 자연어 문장으로만 구성되어야 합니다. 문장은 분석 보고서 형식을 유지하십시오. (객관적·간결)
"""

# --- 3. RAG 요약 함수 ---

def summarize_rag_results(user_query: str, rag_results: dict) -> str:
    """
    gpt-4o를 호출하여 RAG 검색 결과를 요약합니다.
    
    Args:
        user_query: 사용자의 원본 자연어 질문
        rag_results: 'rag_search_pipeline.py'가 반환한 딕셔너리
                     (v1의 형식이든, v2의 형식이든 모두 처리 가능)
    
    Returns:
        LLM이 생성한 자연어 요약 답변 (str)
    """
    
    if not client:
        return "오류: OpenAI 클라이언트가 초기화되지 않았습니다."

    # [수정] v1 결과(total_respondents)와 v2 결과(answer_data)를 모두 고려
    if not rag_results or (
        not rag_results.get('answer_data') and 
        not rag_results.get('total_respondents')
    ):
        return "데이터베이스에서 관련 정보를 찾지 못했습니다."

    try:
        # DB 결과를 LLM이 읽을 수 있도록 JSON 문자열로 변환
        safe_results = {}
        
        # v1 JSON (사용자가 제공한 샘플)을 가정
        if 'total_respondents' in rag_results:
             # 벡터(a_vector)는 LLM에 불필요하므로 제외하고 전달
            safe_results = {
                "total_respondents_in_filter": rag_results.get('total_respondents'),
                "total_answers_found": rag_results.get('total_answers'),
                "sample_answers": [
                    {k: v for k, v in answer.items() if k != 'a_vector'} 
                    for answer in rag_results.get('answer_data', [])[:20] # 너무 길어지지 않게 20개만
                ]
            }
        # v2 (GROUP BY) JSON을 가정
        elif rag_results.get('answer_data'):
             safe_results = {
                "total_unique_answers_found": len(rag_results.get('answer_data', [])),
                "grouped_answers_by_similarity": [
                    {k: v for k, v in answer.items() if k != 'a_vector'} 
                    for answer in rag_results['answer_data'] # v2는 이미 Top-K로 정제됨
                ]
             }
        else:
             safe_results = rag_results

        results_str = json.dumps(safe_results, ensure_ascii=False, indent=2)
        
        # LLM에게 전달할 사용자 프롬프트 구성
        user_prompt_content = f"""
[원본 사용자 질문]
"{user_query}"

[DB 검색 결과 (JSON)]
{results_str}

[지침]
위 시스템 프롬프트의 지침에 따라, 'DB 검색 결과'를 바탕으로 '원본 사용자 질문'에 대한 자연어 요약 답변을 생성하십시오.
"""
        
        print(f"\n>>> [GPT-4o] 요약 생성 시도... (입력 데이터 크기: {len(results_str)} bytes)")

        response = client.chat.completions.create(
            model="gpt-4o", # 또는 "gpt-4o-mini" (더 빠르고 저렴함)
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt_content}
            ],
            temperature=0.5 # 사실 기반의 답변을 위해 0.0~0.7 사이 권장
        )
        
        summary = response.choices[0].message.content
        print(">>> [GPT-4o] 요약 생성 완료.")
        return summary

    except Exception as e:
        print(f"XXX [오류] GPT-4o 요약 중 오류 발생: {e}")
        return f"답변 생성 중 오류가 발생했습니다: {e}"

# --- 4. 메인 실행 (테스트용) ---
if __name__ == "__main__":
    
    # 1. 테스트할 원본 사용자 질문
    mock_user_query = "서울 거주하는 30대 남성의 직업 중 전문직인 사람"
    
    # 2. 'rag_search_pipeline.py' (v1)이 반환했다고 가정한 JSON (사용자님이 제공한 샘플)
    mock_rag_results = {
      "total_respondents": 461,
      "total_answers": 1358,
      "unique_respondents_count": 461,
      "answer_data": [ # (v1 코드에서는 'answer_data' 키를 사용했습니다)
        {
          "respondent_id": "w102849562302896",
          "question_id": "w2_Q4",
          "q_title": "최종학력",
          "answer_value": "3",
          "answer_text": "대학교 졸업"
        },
        {
          "respondent_id": "w102849562302896",
          "question_id": "w2_Q5",
          "q_title": "직업",
          "answer_value": "3",
          "answer_text": "경영/관리직 (사장, 대기업 간부, 고위 공무원 등)"
        },
        {
          "respondent_id": "w10337438326167",
          "question_id": "w2_Q5",
          "q_title": "직업",
          "answer_value": "4",
          "answer_text": "사무직 (기업체 차장 이하 사무직 종사자, 공무원 등)"
        },
        {
          "respondent_id": "w10337438326167",
          "question_id": "w2_Q5",
          "q_title": "직업",
          "answer_value": "5",
          "answer_text": "전문직 (의사, 변호사, 교수, 엔지니어, 디자이너 등)"
        }
        # (...
      ]
    }

    print("--- RAG 요약 모듈 테스트 ---")
    
    # 3. 요약 함수 실행
    final_summary = summarize_rag_results(mock_user_query, mock_rag_results)
    
    print("\n--- 최종 요약 답변 ---")
    print(final_summary)

    # --- 테스트 2 (데이터가 없는 경우) ---
    print("\n--- RAG 요약 모듈 테스트 2 (결과 없음) ---")
    mock_rag_results_empty = {
        "total_respondents": 0,
        "total_answers": 0,
        "answer_data": []
    }
    final_summary_empty = summarize_rag_results(mock_user_query, mock_rag_results_empty)
    print(final_summary_empty)