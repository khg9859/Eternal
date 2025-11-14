## 1. 프로젝트 클론 및 실행 방법

```sh
git clone -b leader https://github.com/khg9859/Eternal.git
cd Eternal
npm install
npm start
```

---

## 2. 기술 스택

### Frontend

- React 18
- Tailwind CSS
- Chart.js
- Framer Motion
- React Router v6

### Backend (예정)

- FastAPI 또는 Express
- PostgreSQL + pgvector
- LangChain 기반 RAG 구조

### Infra (예정)

- AWS EC2 / RDS

---

## 3. 현재 구현된 기능

1. 자연어 기반 질의 입력 후 분석 리포트 화면 렌더링
2. AI Summary 요약 카드
3. Quick Stats 간단 통계
4. Chart.js 기반 데이터 시각화
   - 인구통계(Bar)
   - 카테고리 비중(Doughnut)
   - 월별 트렌드(Line)
   - 감정/신뢰도(Bar + Line)
5. AI 챗봇 UI
   - 자연어 질문 응답
   - 투명도 조절 기능
   - 메시지 자동 스크롤 지원

---

## 4. 미완성 / 예정 기능

1. **데이터베이스 연동**

   - 현재는 더미 데이터 기반
   - PostgreSQL + pgvector 연동 예정

2. **LLM 연동 (LangChain)**

   - 현재는 프론트 임시 응답
   - RAG 기반 구조로 확장 예정

3. **ChartSection 다크모드 개선**
   - 일부 텍스트가 다크모드에서 흐려보이는 문제 존재
   - darkMode 토글 시 차트 재렌더링 필요

---

## 5. 프로젝트 디렉토리 구조

```
Eternal
 ├── public/
 │    ├── bg.mp4
 │    ├── bg1.mp4
 │    └── index.html
 │
 ├── src/
 │    ├── components/
 │    │    ├── AIChatInterface.js
 │    │    ├── AISummary.js
 │    │    ├── ChartSection.js
 │    │    ├── DashboardHeader.js
 │    │    ├── Logo.js
 │    │    ├── QuickStats.js
 │    │    └── SidePanel.js
 │    │
 │    ├── pages/
 │    │    ├── HomePage.js
 │    │    └── ResultsPage.js
 │    │
 │    ├── App.js
 │    ├── index.js
 │    └── index.css
 │
 ├── package.json
 ├── package-lock.json
 ├── README.md
 ├── PROJECT_REPORT.md
 ├── LICENSE
 └── .gitignore
```

---

## 6. 주요 파일 설명

### components/

- **AIChatInterface.js**  
  AI 챗봇 UI, 메시지 핸들링, 투명도 조절 기능 포함

- **AISummary.js**  
  자연어 분석 요약 카드

- **ChartSection.js**  
  Chart.js 기반 4종 그래프 생성

- **QuickStats.js**  
  통계 3개를 카드 형태로 제공

- **DashboardHeader.js**  
  대시보드 상단 헤더 UI

- **SidePanel.js**  
  오른쪽 고정 패널

---

### pages/

- **HomePage.js**  
  메인 화면, 검색 입력 후 ResultsPage로 이동

- **ResultsPage.js**  
  자연어 분석 결과 대시보드 렌더링 (요약, 그래프, 챗봇 포함)

---

### 기타 파일

- **index.js**  
  React 프로젝트 엔트리포인트
- **index.css**  
  Tailwind 및 전역 스타일
- **App.js**  
  전체 라우팅

---

## 7. 향후 개발 계획

- LLM 기반 RAG 파이프라인 완성
- PostgreSQL + pgvector 기반 임베딩 검색
- 데이터셋 자동 요약 및 통계 처리
- 다크모드 UI 개선
- 결과 페이지 고도화

8. ESLint Warning 안내

현재 RAG 백엔드 연동이 아직 이루어지지 않아 useEffect 훅을 임시로 사용하지 않는 상태입니다.
이에 다음과 같은 ESLint 경고가 나타나는 것은 정상입니다.

[eslint] useEffect is defined but never used

이는 백엔드 API가 연결되면 자동으로 사라질 예정이며
프론트엔드 UI 동작에는 전혀 문제가 없습니다.

불필요한 경고를 숨기고 싶다면 아래처럼 사용할 수 있습니다.

// eslint-disable-next-line no-unused-vars

9. Frontend ↔ Backend RAG API 명세 (JSON 기반)

프론트엔드는 RAG 서버와 다음 구조로 통신하게 됩니다.
FastAPI 기준이지만 Express로도 동일한 JSON 형식 사용 가능합니다.

### 9.1 Summary API

POST /rag/summary

Request
{
"query": "30대 남성의 소비 패턴"
}

Response
{
"summary": [
"30대 남성은 식품과 온라인 쇼핑 지출 비중이 높습니다.",
"평균 결제 금액이 전 세대 대비 약 15% 높습니다.",
"모바일 결제 사용률이 증가했습니다."
]
}

### 9.2 Quick Stats API

POST /rag/stats

Request
{
"query": "30대 남성"
}

Response
{
"stats": [
{
"title": "주요 관심 카테고리",
"value": "식품 · 쇼핑 · 구독",
"trend": "상승",
"change": "+8.7%",
"desc": "최근 3개월간 지출 비중 증가"
},
{
"title": "평균 이용 빈도",
"value": "월 18회",
"trend": "활동성 증가",
"change": "+2.4%",
"desc": "모바일 결제 사용률 상승 영향"
}
]
}

### 9.3 Chart Section API

POST /rag/chart

Request
{
"query": "30대 남성 소비 트렌드"
}

Response
{
"demographics": {
"20대": 24,
"30대": 41,
"40대": 28,
"50대": 7
},
"category_ratio": {
"식품": 30,
"패션": 25,
"IT": 20,
"여가": 15,
"기타": 10
},
"monthly_trend": {
"1월": 82,
"2월": 90,
"3월": 96,
"4월": 103,
"5월": 115,
"6월": 122
},
"sentiment_score": {
"긍정": 68,
"중립": 22,
"부정": 10
},
"trust_index": [84, 86, 87, 89, 90, 92]
}

### 9.4 Chat API

POST /chat

Request
{
"query": "30대 남성의 온라인 쇼핑 특징은?"
}

Response
{
"answer": "30대 남성은 모바일 기반의 온라인 쇼핑 비중이 높으며 구독형 서비스 이용률도 지속 상승하고 있습니다."
}

10. RAG 서버 아키텍처 예시
    사용자 질의 → FastAPI → Embedding(pgvector) 유사도 검색 →  
    LangChain Prompt → LLM(GPT) → 응답 생성 → 프론트로 반환

11. 프론트 코드 구조 (RAG 연동 지점)

/components/AISummary.js

POST /rag/summary 호출 예정

/components/QuickStats.js

POST /rag/stats 호출 예정

/components/ChartSection.js

POST /rag/chart 호출 예정

/components/AIChatInterface.js

POST /chat 호출 예정
