# Backend - FastAPI + LangChain RAG

자연어 질의 처리 및 데이터 검색을 위한 백엔드 서버

## 기술 스택

- **FastAPI**: 고성능 비동기 웹 프레임워크
- **LangChain**: LLM 파이프라인 관리
- **PostgreSQL + pgvector**: 벡터 임베딩 기반 유사도 검색
- **OpenAI GPT**: 자연어 이해 및 응답 생성

## 프로젝트 구조

```
backend/
├── main.py              # FastAPI 서버 엔트리포인트
├── LLMlangchan.py       # LLM RAG 파이프라인
├── search/              # 검색 및 RAG 모듈
│   ├── ai_summary.py    # AI 요약 생성
│   ├── makeSQL.py       # SQL 쿼리 생성
│   ├── parsing.py       # 데이터 파싱
│   └── rag_pipeline.py  # RAG 파이프라인
├── requirements.txt     # Python 의존성
├── Dockerfile          # Docker 이미지 설정
└── docker-compose.yml  # Docker 컨테이너 오케스트레이션
```

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

루트 디렉토리의 `.env` 파일에 다음 변수를 설정:

```
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### 4. 서버 실행

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

서버가 http://localhost:8000 에서 실행됩니다.

## Docker 실행

```bash
docker-compose up -d
```

## API 엔드포인트

- `GET /`: 헬스 체크
- `POST /search`: 자연어 검색
- `POST /chat`: AI 챗봇 대화
- `GET /docs`: Swagger API 문서

## 개발

- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
