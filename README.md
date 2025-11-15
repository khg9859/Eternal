# 🌟 Eternal - AI 기반 패널 데이터 분석 플랫폼

패널 데이터를 AI로 분석하고 시각화하는 통합 플랫폼입니다.

## 📋 프로젝트 구조

```
Eternal/
├── Eternal_FE/     # 프론트엔드 (React)
├── Eternal_SV/     # 백엔드 서버 (FastAPI)
└── Eternal_DT/     # 데이터 처리 (RAG Pipeline)
```

## 🚀 주요 기능

- **AI 기반 질의응답**: 자연어로 패널 데이터 질문
- **실시간 데이터 시각화**: 차트와 그래프로 데이터 분석
- **RAG 파이프라인**: LangChain 기반 검색 증강 생성
- **인터랙티브 대시보드**: 직관적인 UI/UX

## 🛠️ 기술 스택

### 프론트엔드 (Eternal_FE)
- React 18
- Tailwind CSS
- Chart.js
- Axios

### 백엔드 (Eternal_SV)
- FastAPI
- Python 3.9+
- LangChain
- OpenAI API

### 데이터 처리 (Eternal_DT)
- PostgreSQL
- Vector DB (Embedding)
- RAG Pipeline

## 📦 설치 및 실행

### 1. 프론트엔드 실행

```bash
cd Eternal_FE/Eternal
npm install
npm start
```

프론트엔드는 `http://localhost:3000`에서 실행됩니다.

### 2. 백엔드 실행

```bash
cd Eternal_SV
pip install -r requirements.txt
python main.py
```

백엔드는 `http://localhost:8000`에서 실행됩니다.

### 3. 환경 변수 설정

`Eternal_SV/.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=your_database_url
```

## 📊 주요 화면

### 홈페이지
- AI 기반 검색 인터페이스
- 질문 입력 및 분석 시작

### 결과 페이지
- **QuickStats**: 4개 차트에 대한 핵심 인사이트 요약
- **나이대 통계 분포**: 연령대별 참여 현황
- **지역별 응답률 비중**: 지역별 분포 분석
- **데이터 테이블**: 상세 응답 데이터
- **응답 순위 분석**: 상위 응답 집중도

## 🔧 개발 가이드

### API 엔드포인트

#### POST `/rag/query`
사용자 질문을 받아 AI 분석 결과 반환

**Request:**
```json
{
  "query": "50대 사용자의 주요 관심사는?"
}
```

**Response:**
```json
{
  "statistics": [...],
  "demographics": {...},
  "summary": "..."
}
```
