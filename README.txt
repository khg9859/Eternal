1. 필요한 pip 요소들
pip install fastapi uvicorn
pip install langchain-core langchain-openai langchain-anthropic python-dotenv pydantic
pip install psycopg2-binary pgvector
pip install sentence-transformers numpy

##다있는거
pip install fastapi uvicorn psycopg2-binary pgvector numpy sentence-transformers langchain-core langchain-openai langchain-anthropic python-dotenv pydantic


1. 코드 작동 방식

사용자 질문 -> 
gpt-4o-mini(이걸로 할지 확정 아님)가 이게 db를 확인해야 할 질문인지, 
단순 질문인지, 이전에 확인했던 db와 관련있는 질문인지 판단.

a. db가 확인해야 할 질문일 경우 아래 과정으로 수행됨.
----------------------------------------------------------------------------------
1. 벡터 유사도 검색 과정에서 랭체인 앱이 DB가 수행할 유사도 검색에 2가지 조건을 넣음.
- 질문 벡터와 가까운 문서를 넣어라
- 유사도 순서대로 가장 관련성 높은 20개만 반환하라
1. 추출된 데이터 레코드들이 langchain 로직으로 python메모리에 담긴 document 타입으로 변환.
2. document 객체 리스트 임시 아이디를 포함하는 문자열로 변환

<aside>
💡

LLM(gpt-4o)가 읽을 수 있게 하기 위해서는 문자열로 받아 프롬프트 안에 넣어야 하기 때문임.

</aside>

1. 문자열이 LLM 프롬프트로 들어가 LLM이 20개 문서 중 관련있는 3개의 문서를 추림.
2. 랭체인 앱에 있는 20개의 문서 중 17개를 없앰.
3. 필터링된 3개의 객체에서 claud가 프롬프트를 통해 결론을 도출.

장점 : 20개와 3개로 정한 것은 언제든 바꿀 수 있어서, 환각 정도, 정확도 정도, 가격에 따라 유동적으로 변환 가능. 문서를 선별하는 과정에 LLM이 들어감으로써 환각 정도를 줄일 수 있음.

20개의 문서를 더 늘릴 경우: 프롬프트에 넣게 될 토큰 수가 많아져 가격이 오르지만, 표본 수가 많아져 정확도가 높아짐.

3개 문서를 더 늘릴 경우: 더 정확하지 않을 수 있는 문서 수가 많아져 정확도는 낮아지지만, 사용자가 문서에 적힌 자료 수 이상을 요구할 경우 대답하기 곤란해짐.
------------------------------------------------------------------------------------

b. db가 단순 질문일 경우 : gpt-4o-mini(이걸로 할지 확정 아님)가 단순 답변 생성.

c. db가 이전에 나온 자료로 대답 가능한 경우 : 