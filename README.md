

## 로컬에서 라이브러리 받기
pip install -r requirements.txt

## 가상환경 만들기
python -m venv venv
venv\Scripts\activate
## 설치해야하는 라이브러리(가상환경에서)
pip install -U flask flask-cors python-dotenv psycopg2-binary numpy openai
pip install -U langchain langchain-core langchain-community langchain-openai langchain-huggingface
pip install -U sentence-transformers
pip install -U langchain-huggingface sentence-transformers
pip install -U langchain-openai
pip install -U python-dotenv

.env파일에서 오픈AI 키는 카톡으로 알려드릴게요.