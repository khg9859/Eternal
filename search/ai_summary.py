# -*- coding: utf-8 -*-
"""
RAG 답변 요약기 v2 (LLM Call #3: Synthesize - Aggregated Data)
... (주석 동일) ...
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
    - `value_counts`의 **"total_responses": 숫자**는 주아진 자료의 총 응답자 수 입니다. 이를 꼭 넣어서 총 응답자 수를 출력하시오.
    - '총 응답자 수'를 기준으로 각 항목의 '비율(%)'을 계산하십시오.
    - **가장 비율이 높은 항목(1순위)**을 명확히 밝히고, **주요 항목들(2, 3순위 등)의 수치와 비율을 비교 분석**하십시오.
    - **(예시) "총 461명 중 '미혼'이 333명(72.2%)으로 과반수를 차지했으며, '기혼'은 125명(27.1%)으로 그 뒤를 이었습니다."**처럼, 핵심 통계와 비교 분석을 포함하여 2-3문장으로 요약하십시오.

4.  **[리포트 생성]**
    - 서론("분석 결과는...")이나 결론("이러한 결과는...") 같은 군더더기를 피하고, **핵심 분석 내용**으로 바로 시작하십시오.
    - **사실, 수치, 비율, 그리고 주요 항목 간의 비교**에 집중하십시오.
    - 사용자의 쿼리 입력이 주어진 자료와 관련이 있으면, 유저의 '필터 조건'을 언급하며 리포트를 생성하시오.(예시 : '유저의 입력: 30대 남성이 선호하는 직무', 주어진 데이터와 일치하면 '"30대 남성이 선호하는 직무는" {리포트 내용}')
    
5.  **[형식]** 최종 답변은 2-3문장의 간결하면서도 **분석적인** 한국어 문단이어야 합니다.

6. **"total_responses": 숫자**는 주아진 자료의 총 응답자 수 입니다. 이를 꼭 넣어서 총 응답자 수를 출력하시오.


"""
# --- 3. RAG 요약 함수 ---
## 파싱 전 자연어 입력 그대로 넣기 : user_query (테스트로 아무내용/공백 넣었지만 테스트에 큰 영향을 끼치지 않았음.. 다른 사람도 다른 데이터를 넣은 테스트하길 바람)
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

    # [수정] agg_results가 'query_results' 키를 포함하는지 확인
    if not agg_results or not agg_results.get('query_results'):
        print("[Debug] 입력된 agg_results에 'query_results' 키가 없습니다.")
        return "관련 통계 데이터를 찾지 못했습니다."

    try:
        # DB 결과를 LLM이 읽을 수 있도록 JSON 문자열로 변환
        # (샘플 답변 'answers' 또는 'answers_sample' 리스트는 LLM의 토큰을 낭비하므로,
        #  핵심 정보인 'q_title'과 'value_counts'만 전달)
        
        safe_results = {}
        # [수정] agg_results.get('query_results')가 딕셔너리가 맞는지 확인
        query_results_data = agg_results.get('query_results', {})
        if not isinstance(query_results_data, dict):
             print(f"[Debug] 'query_results'가 딕셔너리 형식이 아닙니다: {type(query_results_data)}")
             return "관련 통계 데이터를 찾지 못했습니다."

        for q_id, data in query_results_data.items():
            if data and 'value_counts' in data: # [수정] value_counts가 있는지 확인
                safe_results[q_id] = {
                    "q_title": data.get("q_title"),
                    "value_counts": data.get("value_counts")
                    # 'answers' 또는 'answers_sample' 샘플 리스트는 의도적으로 제외
                }
            else:
                print(f"[Debug] {q_id} 항목에 'value_counts'가 없습니다.")
        
        if not safe_results:
            return "분석할 'value_counts' 데이터가 없습니다."

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
        
        print(f"\n>>> [GPT] 상세 분석 시도... (입력 데이터 크기: {len(results_str)} bytes)")

        # [수정] "gpt-5.1" -> "gpt-4o" (실제 사용 가능한 모델명으로)
        response = client.chat.completions.create(
            model="gpt-5.1", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt_content}
            ],
            temperature=0.3 # 분석 리포트의 일관성을 위해 temperature 낮춤
        )
        
        summary = response.choices[0].message.content
        print(">>> [GPT] 상세 분석 완료.")
        return summary

    except Exception as e:
        print(f"XXX [오류] GPT 요약 중 오류 발생: {e}")
        return f"답변 생성 중 오류가 발생했습니다: {e}"

# --- 4. 메인 실행 (테스트용) ---
# --- 4. 메인 실행 (테스트용) ---
if __name__ == "__main__":
    
    # 1. 테스트할 원본 사용자 질문
    mock_user_query = "912세 여성이 좋아하는 취미는?"
    
    # 2. 'rag_search_pipeline' 등이 반환했다고 가정한 '집계 JSON'
    # [수정] Python 딕셔너리 문법 오류 수정
    # 'query_results'와 'w2_Q5_1' 키 추가
    mock_agg_results = {
      "query_results": {
        "w2_Q5_1": {
          "q_title": "직무",
          "codebook_id": "w2_Q5_1",
          "value_counts": {
            "total_responses": 1877,
            "생산•정비•기능•노무": 233,
            "디자인": 23,
            "건설•건축•토목•환경": 143,
            "유통•물류•운송•운전": 121,
            "의료•간호•보건•복지": 102,
            "무역•영업•판매•매장관리": 110,
            "경영•인사•총무•사무": 177,
            "전자•기계•기술•화학•연구개발": 140,
            "재무•회계•경리": 52,
            "무직": 58,
            "편의점": 3,
            "교육•교사•강사•교직원": 63,
            "IT": 141,
            "운송": 1,
            "문화•스포츠": 23,
            "서비스•여행•숙박•음식•미용•보안": 149,
            "펜션": 1,
            "마케팅•광고•홍보•조사": 54,
            "환경보호": 1,
            "국방": 4,
            "전문직•법률•인문사회•임원": 36,
            "인터넷•통신": 25,
            "금융•보험•증권": 45,
            "취준": 2,
            "휴식": 1,
            "요리사": 1,
            "세탁업": 2,
            "택배": 2,
            "택배배송": 1,
            "사회복지사": 1,
            "카트운반.주차": 1,
            "고객상담•TM": 36,
            "취업준비": 3,
            "소방": 3,
            "구직중": 4,
            "실업급여": 1,
            "전업투자": 1,
            "청소": 1,
            "기타": 1,
            "세계질서, 유지": 1,
            "배달": 1,
            "통합": 1,
            "게임": 12,
            "적, 사살": 1,
            "음식생산, 및, 판매": 1,
            "방송•언론": 8,
            "사무전반적인, 모든것": 1,
            "교육부서": 1,
            "사무, 및, 품질관리": 1,
            "장교": 1,
            "연단위, 변경되는, 보직에, 따라, 다름": 1,
            "용접": 1,
            "품질": 1,
            "대리기사": 1,
            "모바일": 7,
            "교통관련": 1,
            "상품, 기획": 1,
            "프리랜서": 4,
            "아파서, 쉬는중": 1,
            "관세사": 1,
            "제조": 1,
            "보안": 3,
            "포토그래퍼": 1,
            "편집, 인쇄": 1,
            "취준생": 4,
            "아무거, 다해요": 1,
            "경비": 1,
            "종교": 2,
            "취업준비생": 1,
            "지역문화, 발전": 1,
            "방송보조출연": 1,
            "AD보조": 1,
            "범죄수사": 1,
            "컨설팅/기획": 1,
            "유치원": 1,
            "애견호텔": 1,
            "취업준비중": 1,
            "일용직": 1,
            "영상": 1,
            "사회적시업": 1,
            "기사": 1,
            "안보, 국방": 1,
            "프리": 1,
            "아르바이트": 1,
            "영업, 관리, 직무, 희망, 중.": 1,
            "개잡부": 1,
            "백수": 3,
            "구급": 1,
            "잡무": 1,
            "백수라고": 1,
            "행정보조": 1,
            "여러가지": 1,
            "구매팀": 1,
            "엔터테인먼트": 1,
            "장애우들에게, 문화체험": 1,
            "현재, 무직": 1,
            "대행기관, 안전관리자": 1,
            "금형": 1,
            "정부지원": 1,
            "서빙": 1,
            "생산관리(자재피딩)": 1,
            "농사": 1,
            "노가다": 1,
            "항해사": 1,
            "안전": 2,
            "취준샐": 1,
            "상차": 1,
            "청소원": 1,
            "공연": 1,
            "최근에, 무직": 1,
            "요식업": 1,
            "기술영업": 1,
            "판매": 1,
            "축산": 1
          },
          "answers_sample": [
            {
              "answer_id": 426074,
              "mb_sn": "w401072656314696",
              "question_id": "w2_Q5_1",
              "answer_value": "21",
              "codebook_data": {
                "answers": [
                  {
                    "qi_val": "1",
                    "qi_title": "경영•인사•총무•사무"
                  },
                  # ... (중략) ...
                  {
                    "qi_val": "21",
                    "qi_title": "생산•정비•기능•노무"
                  }
                ],
                "q_title": "직무",
                "codebook_id": "w2_Q5_1"
              },
              "answer_value_text": "생산•정비•기능•노무"
            },
            {
              "answer_id": 430792,
              "mb_sn": "w298056470319003",
              "question_id": "w2_Q5_1",
              "answer_value": "14",
              "codebook_data": {
                "answers": [
                  # ... (중략) ...
                  {
                    "qi_val": "21",
                    "qi_title": "생산•정비•기능•노무"
                  }
                ],
                "q_title": "직무",
                "codebook_id": "w2_Q5_1"
              },
              "answer_value_text": "디자인"
            },
            {
              "answer_id": 430583,
              "mb_sn": "w199153663366312",
              "question_id": "w2_Q5_1",
              "answer_value": "20",
              "codebook_data": {
                "answers": [
                  # ... (중략) ...
                  {
                    "qi_val": "21",
                    "qi_title": "생산•정비•기능•노무"
                  }
                ],
                "q_title": "직무",
                "codebook_id": "w2_Q5_1"
              },
              "answer_value_text": "건설•건축•토목•환경"
            }
          ]
        }
      }
    }


    print("--- RAG 상세 분석 모듈 테스트 ---")
    
    # 3. 요약 함수 실행
    final_summary = summarize_agg_results(mock_user_query, mock_agg_results)
    
    print("\n--- 최종 분석 리포트 ---")
    print(final_summary)
