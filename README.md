
## 변경점 ##
App.js에서 기존에 있던 파일 업로드, 데이터 시각화 기능은 뺐습니다.


추가 : server.py : langChain으로 LLM 동작시키는 백엔드 코드
     
      .env : 서버파일의 환경변수 파일

## 로컬에서 라이브러리 받기
pip install -r requirements.txt

## 가상환경 만들기
python -m venv venv

venv\Scripts\activate
## 설치해야하는 라이브러리(가상환경에서)
pip install fastapi uvicorn[standard] 
pip install -U flask flask-cors python-dotenv psycopg2-binary numpy openai

pip install -U langchain langchain-core langchain-community langchain-openai langchain-huggingface

pip install -U sentence-transformers

pip install -U langchain-huggingface sentence-transformers

pip install -U langchain-openai

pip install -U python-dotenv

.env파일에서 오픈AI 키는 카톡으로 알려드릴게요.

## 실행 방법 ## (bash 두개 키고) 

uvicorn server:app --host 0.0.0.0 --port 5000 --reload 

npm start