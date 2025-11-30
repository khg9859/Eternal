# -*- coding: utf-8 -*-
"""
RAG 쿼리 분해기 (Query Deconstructor)

[목적]
사용자의 자연어 입력을 받아, OpenAI의 gpt-4o-mini 모델을 사용해
'metadata 필터링용 JSON'과 '벡터 검색용 텍스트'로 분리합니다.

[필요 라이브러리]
pip install openai python-dotenv

[필요 .env 설정]
OPENAI_API_KEY=sk-xxxxxxxxxxxx
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
    exit()

client = OpenAI(api_key=API_KEY)


# --- 2. LLM에게 전달할 시스템 프롬프트 및 스키마 정의 ---

# [중요] LLM이 참조할 수 있도록, metadata 테이블의 스키마를 명확하게 정의합니다.
METADATA_SCHEMA = """
[Metadata Table Schema]
- 'gender' (VARCHAR): '남성', '여성'
- 'age' (INT): 39, 41 등 (만 나이)
- 'birth_year' (INT): 1984, 1990 등 (출생년도)
- 'region' (VARCHAR): '서울특별시 동대문구', '경기도 광주시', '경기', '서울' 등
- 'mobile_carrier' (VARCHAR): 'SKT', 'KT', 'LGU+', 'Wiz'
"""

# [핵심] LLM이 따라야 할 지침
SYSTEM_PROMPT = f"""
당신은 PostgreSQL 기반의 하이브리드 검색 시스템을 위한 '쿼리 분석기'입니다.
사용자의 자연어 입력을 받으면, [Metadata Table Schema]를 참고하여
다음 두 가지 요소를 추출하는 JSON 객체를 반환해야 합니다.

1. 'filters' (필터링 요소):
   - [Metadata Table Schema]에 정의된 컬럼과 일치하는 모든 '정형 데이터' 조건입니다.
   - '30대'는 'age' 컬럼에 대해 '>=' 30, '<' 40 조건으로 변환해야 합니다.
   - '1990년대생'은 'birth_year' 컬럼에 대해 '>=' 1990, '<' 2000 조건으로 변환해야 합니다.
   - '서울'은 'region' 컬럼에 대해 'LIKE' 연산자와 '서울%' 값으로 변환해야 합니다.
   - 스키마에 없는 조건(예: '결혼', '자녀', '직업')은 'filters'에 절대 포함시키지 마십시오.

2. 'semantic_query' (의미 검색어):
   - 'filters'로 추출되고 남은, 사용자의 순수한 "의미적" 질의입니다.
   - 만약 필터만 있고 의미 검색어가 없다면, 빈 문자열("")을 반환합니다.

[Metadata Table Schema]
{METADATA_SCHEMA}

반드시 지정된 JSON 형식으로만 응답하십시오.
"""

# [중요] LLM이 반환할 JSON의 구조(Schema)를 OpenAI 'tools' 기능으로 정의
QUERY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "metadata 테이블의 컬럼명 (예: 'region', 'age')"},
                    "operator": {"type": "string", "description": "SQL 연산자 (예: '=', 'LIKE', '>=', '<')"},
                    "value": {"type": "string", "description": "SQL WHERE 절에 사용할 값 (예: '서울%', '30', '남성', '여성', '남자', '여자')"}
                },
                "required": ["column", "operator", "value"]
            }
        },
        "semantic_query": {
            "type": "string",
            "description": "필터링 요소를 제외한, 벡터 검색에 사용할 순수 의미 검색어 (예: '경제 만족도')"
        }
    },
    "required": ["filters", "semantic_query"]
}

# --- 3. 쿼리 분해 함수 ---
def parse_query_with_gpt(user_query: str) -> dict:
    """
    gpt-4o-mini를 호출하여 사용자의 자연어 쿼리를
    'filters'와 'semantic_query'로 분해합니다.
    """
    print(f"\n>>> [GPT-4o-mini] 쿼리 분해 시도: \"{user_query}\"")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            # 'tools'를 사용해 LLM이 JSON 스키마를 따르도록 강제
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "extract_query_components",
                        "description": "사용자 쿼리에서 필터와 의미 검색어를 추출합니다.",
                        "parameters": QUERY_JSON_SCHEMA
                    }
                }
            ],
            tool_choice={
                "type": "function", 
                "function": {"name": "extract_query_components"}
            },
            temperature=0.0 # 일관된 결과를 위해 0.0으로 설정
        )
        
        # LLM의 응답에서 JSON 문자열 추출
        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "extract_query_components":
            arguments_str = tool_call.function.arguments
            # JSON 문자열을 Python 딕셔너리로 파싱
            parsed_json = json.loads(arguments_str)
            return parsed_json
        else:
            raise Exception("LLM이 예상된 함수를 호출하지 않았습니다.")

    except Exception as e:
        print(f"XXX [오류] OpenAI API 호출 또는 JSON 파싱 중 오류 발생: {e}")
        # 오류 발생 시, 필터 없이 전체 쿼리를 의미 검색어로 사용 (Fallback)
        return {
            "filters": [],
            "semantic_query": user_query 
        }

# --- 4. 메인 실행 (테스트용) ---
if __name__ == "__main__":
    
    # [테스트 1] 하이브리드 쿼리 (필터 + 의미)
    query1 = "서울에 거주하는 30대 남성의 전문직인 직종"
    result1 = parse_query_with_gpt(query1)
    print("--- [결과 1] ---")
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    # [예상 결과]
    # {
    #   "filters": [
    #     {"column": "region", "operator": "LIKE", "value": "서울%"},
    #     {"column": "age", "operator": ">=", "value": "30"},
    #     {"column": "age", "operator": "<", "value": "40"},
    #     {"column": "gender", "operator": "=", "value": "남성"}
    #   ],
    #   "semantic_query": "경제 만족도"
    # }

