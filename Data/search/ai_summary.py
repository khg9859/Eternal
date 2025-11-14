# -*- coding: utf-8 -*-
"""
RAG 답변 요약기 v2 (LLM Call #3: Synthesize - Aggregated Data)

[목적]
'rag_search_pipeline.py'가 반환한 '사전 집계된 통계' JSON을 입력받아,
gpt-4o 모델을 사용해 '수치'와 '비율'을 포함한
상세한 자연어 요약 및 분석 리포트를 생성합니다.

[v2 변경 사항]
- v1 (rag_summarizer.py)과 달리, 원본 답변 리스트가 아닌
  'value_counts' (집계 데이터)를 입력받는 것을 전제로 합니다.
- SYSTEM_PROMPT가 '비율 계산' 및 '수치 분석'을 명시적으로 지시합니다.
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
    raise EnvironmentError("OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")

try:
    # (참고: gpt-5.1은 현재 사용 불가능하므로, gpt-4o를 사용합니다)
    client = OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"XXX [오류] OpenAI 클라이언트 초기화 실패: {e}")
    client = None

# --- 2. LLM에게 전달할 시스템 프롬프트 정의 ---

SYSTEM_PROMPT = """
당신은 '설문조사 데이터 분석 애널리스트'입니다.
'원본 사용자 질문'과 '사전 집계된 통계 데이터(JSON)'가 제공됩니다.
당신의 임무는 이 데이터를 기반으로, 사용자의 질문에 대한 **핵심 분석이 포함된 간결한 요약**을 생성하는 것입니다.

[지침]
1.  **[매우 중요]** 'DB 검색 결과'는 사용자의 '필터 조건'(예: 30대, 남성, 서울)이 **'이미 적용된'** 결과입니다. 
    당신은 이 필터링된 그룹 내의 통계를 분석하는 데만 집중하십시오.

2.  **[데이터 구조]** `value_counts`(답변별 응답자 수)가 핵심 정보입니다.

3.  **[핵심 임무: 분석 및 요약]**
    - `value_counts`의 모든 값을 합산하여 '총 응답자 수'를 계산하십시오. (예: 333 + 125 + 3 = 461명)
    - '총 응답자 수'를 기준으로 각 항목의 '비율(%)'을 계산하십시오.
    - **가장 비율이 높은 항목(1순위)**을 명확히 밝히고, **주요 항목들(2, 3순위 등)의 수치와 비율을 비교 분석**하십시오.
    - **(예시) "총 461명 중 '미혼'이 333명(72.2%)으로 과반수를 차지했으며, '기혼'은 125명(27.1%)으로 그 뒤를 이었습니다."**처럼, 핵심 통계와 비교 분석을 포함하여 2-3문장으로 요약하십시오.

4.  **[리포트 생성]**
    - 서론("분석 결과는...")이나 결론("이러한 결과는...") 같은 군더더기를 피하고, **핵심 분석 내용**으로 바로 시작하십시오.
    - **사실, 수치, 비율, 그리고 주요 항목 간의 비교**에 집중하십시오.
    
5.  **[형식]** 최종 답변은 2-3문장의 간결하면서도 **분석적인** 한국어 문단이어야 합니다.
"""

# --- 3. RAG 요약 함수 ---

def summarize_agg_results(user_query: str, agg_results: dict) -> str:
    """
    gpt-4o를 호출하여 '집계된(aggregated)' RAG 검색 결과를 요약 및 분석합니다.
    
    Args:
        user_query: 사용자의 원본 자연어 질문
        agg_results: 'query_results' 키를 포함하는 집계 딕셔너리
    
    Returns:
        LLM이 생성한 자연어 요약 답변 (str)
    """
    
    if not client:
        return "오류: OpenAI 클라이언트가 초기화되지 않았습니다."

    if not agg_results or not agg_results.get('query_results'):
        return "관련 통계 데이터를 찾지 못했습니다."

    try:
        # DB 결과를 LLM이 읽을 수 있도록 JSON 문자열로 변환
        # (샘플 답변 'answers' 리스트는 LLM의 토큰을 낭비하므로,
        #  핵심 정보인 'q_title'과 'value_counts'만 전달)
        
        safe_results = {}
        for q_id, data in agg_results.get('query_results', {}).items():
            safe_results[q_id] = {
                "q_title": data.get("q_title"),
                "value_counts": data.get("value_counts")
                # 'answers' 샘플 리스트는 제외
            }
        
        # 실제 LLM에 전달할 최종 JSON
        final_json_input = {
            "query_results": safe_results
        }
        
        results_str = json.dumps(final_json_input, ensure_ascii=False, indent=2)
        
        # LLM에게 전달할 사용자 프롬프트 구성
        user_prompt_content = f"""
[원본 사용자 질문]
"{user_query}"

[집계된 통계 데이터 (JSON)]
{results_str}

[지침]
위 시스템 프롬프트의 지침에 따라, 'DB 검색 결과'의 'value_counts'를 분석하여
'수치'와 '비율(%)'이 포함된 상세한 자연어 요약 리포트를 생성하십시오.
"""
        
        print(f"\n>>> [GPT-4o] 상세 분석 시도... (입력 데이터 크기: {len(results_str)} bytes)")

        response = client.chat.completions.create(
            model="gpt-5.1", # gpt-5.1 대신 gpt-4o 사용
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt_content}
            ],
            temperature=0.3 # 분석 리포트의 일관성을 위해 temperature 낮춤
        )
        
        summary = response.choices[0].message.content
        print(">>> [GPT-4o] 상세 분석 완료.")
        return summary

    except Exception as e:
        print(f"XXX [오류] GPT-4o 요약 중 오류 발생: {e}")
        return f"답변 생성 중 오류가 발생했습니다: {e}"

# --- 4. 메인 실행 (테스트용) ---
if __name__ == "__main__":
    
    # 1. 테스트할 원본 사용자 질문
    mock_user_query = "필터링된 응답자들의 결혼 여부를 상세히 분석해줘."
    
    # 2. 'rag_search_pipeline' 등이 반환했다고 가정한 '집계 JSON'
    # (사용자님이 제공한 샘플을 기반으로 완전한 JSON 구성)
    mock_agg_results = {
      "query_results": {
        "w2_Q1": {
          "q_title": "결혼여부",
          # 'total_respondents' 키는 없다고 가정 (LLM이 계산하도록)
          "answers": [
            # 이 샘플 데이터는 LLM에 전달되지 않음
            {
              "answer_id": 1311276,
              "mb_sn": "w209536081994405",
              "answer_value_text": "미혼"
            },
            {
              "answer_id": 1311365,
              "mb_sn": "w209648047130979",
              "answer_value_text": "미혼"
            }
          ],
          "value_counts": {
            "미혼": 333,
            "기혼": 125,
            "기타(사별/이혼 등)": 3
          }
        }
        # (만약 다른 질문이 있다면 "w2_Q2": { ... } 가 추가될 수 있음)
      }
    }


    print("--- RAG 상세 분석 모듈 테스트 ---")
    
    # 3. 요약 함수 실행
    final_summary = summarize_agg_results(mock_user_query, mock_agg_results)
    
    print("\n--- 최종 분석 리포트 ---")
    print(final_summary)