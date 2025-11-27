# 🔗 Eternal_FE ↔ Eternal_SV 백엔드 통합 가이드

## ✅ 완료된 작업

### 백엔드 (Eternal_SV/main.py)
다음 3개의 엔드포인트가 추가되었습니다:

1. **`POST /rag/search`** - AI 챗봇 대화
   - 입력: `{ "query": "질문", "session_id": "세션ID" }`
   - 출력: `{ "answer": "AI 답변", "sources": [...] }`

2. **`POST /rag/charts`** - 차트 데이터 생성
   - 입력: `{ "query": "질문" }`
   - 출력: 
     ```json
     {
       "demographics": { "20대": 24, "30대": 41, ... },
       "category_ratio": { "식품": 30, "패션": 25, ... },
       "monthly_trend": { "1월": 82, "2월": 90, ... },
       "sentiment_score": { "긍정": 68, "중립": 22, "부정": 10 },
       "trust_index": [84, 86, 87, 89, 90, 92]
     }
     ```

3. **`POST /rag/summary`** - AI 요약 생성
   - 입력: `{ "query": "질문" }`
   - 출력: `{ "summary": ["문장1", "문장2", ...] }`

### 프론트엔드 (Eternal_FE/Eternal/src/components/)

1. **AIChatInterface.js** ✅
   - `http://localhost:8000/rag/search` 연동
   - 실시간 AI 대화 기능

2. **ChartSection.js** ✅
   - `http://localhost:8000/rag/charts` 연동
   - 4개 차트 자동 렌더링 (인구통계, 카테고리, 트렌드, 감정분석)

3. **AISummary.js** ✅
   - `http://localhost:8000/rag/summary` 연동
   - AI 요약 텍스트 표시

---

## 🚀 실행 방법

### 1단계: 환경 설정

**OpenAI API 키 설정** (필수!)
```bash
cd Eternal_SV
nano .env  # 또는 텍스트 에디터로 열기
```

`.env` 파일에서 유효한 API 키로 변경:
```env
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
```

### 2단계: 백엔드 실행

```bash
cd Eternal_SV
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 3단계: 프론트엔드 실행

**새 터미널 창에서:**
```bash
cd Eternal_FE/Eternal
npm install  # 처음 한 번만
npm start
```

브라우저가 자동으로 `http://localhost:3000`을 엽니다.

---

## 🧪 테스트 방법

### 1. 홈페이지에서 검색
- "30대 남성의 소비 패턴" 입력
- Results 페이지로 이동

### 2. AI 요약 확인
- 상단에 AI 요약 카드가 표시됨
- 백엔드에서 RAG 기반 요약 생성

### 3. 차트 확인
- 4개의 차트가 자동으로 렌더링
- 실제 DB 데이터 기반 (연령대, 지역 등)

### 4. AI 챗봇 테스트
- 우측 하단 "💬 챗봇 열기" 클릭
- "데이터의 평균값은?" 같은 질문 입력
- 실시간 AI 응답 확인

---

## 🔧 문제 해결

### 1. API 키 오류 (401 Unauthorized)
```
Error: Incorrect API key provided
```
**해결:** `.env` 파일의 `OPENAI_API_KEY`를 유효한 키로 변경

### 2. 백엔드 연결 실패
```
Failed to fetch
```
**해결:** 
- 백엔드가 실행 중인지 확인 (`python main.py`)
- `http://localhost:8000` 접속 테스트

### 3. CORS 오류
```
Access-Control-Allow-Origin error
```
**해결:** `main.py`의 CORS 설정 확인 (이미 설정됨)

### 4. 데이터베이스 연결 오류
```
Database connection failed
```
**해결:** 
- PostgreSQL 실행 확인
- `.env`의 DB 설정 확인

---

## 📊 데이터 흐름

```
사용자 입력 (Eternal_FE)
    ↓
HomePage → ResultsPage
    ↓
┌─────────────────────────────────────┐
│  3개 컴포넌트가 동시에 API 호출      │
├─────────────────────────────────────┤
│  1. AISummary → /rag/summary        │
│  2. ChartSection → /rag/charts      │
│  3. AIChatInterface → /rag/search   │
└─────────────────────────────────────┘
    ↓
Eternal_SV 백엔드 (main.py)
    ↓
LLMlangchan.py (RAG 파이프라인)
    ↓
PostgreSQL + pgvector
    ↓
OpenAI GPT-4o-mini
    ↓
응답 반환 → 프론트엔드 렌더링
```

---

## 🎯 다음 단계 (선택사항)

### 1. 실시간 데이터 분석 강화
- `hybrid_answer()` 결과를 차트 데이터로 변환
- 질문에 따라 동적으로 차트 타입 변경

### 2. 세션 관리
- 사용자별 대화 히스토리 저장
- Redis 또는 DB 세션 관리

### 3. 캐싱
- 동일 질문에 대한 응답 캐싱
- 차트 데이터 캐싱으로 성능 향상

### 4. 에러 핸들링 개선
- 더 자세한 에러 메시지
- 재시도 로직 추가

---

## 📝 주요 파일 목록

### 백엔드
- `Eternal_SV/main.py` - FastAPI 서버
- `Eternal_SV/LLMlangchan.py` - RAG 파이프라인
- `Eternal_SV/.env` - 환경 변수 (API 키, DB 설정)

### 프론트엔드
- `Eternal_FE/Eternal/src/App.js` - 메인 앱
- `Eternal_FE/Eternal/src/pages/HomePage.js` - 홈페이지
- `Eternal_FE/Eternal/src/pages/ResultsPage.js` - 결과 페이지
- `Eternal_FE/Eternal/src/components/AIChatInterface.js` - 챗봇
- `Eternal_FE/Eternal/src/components/ChartSection.js` - 차트
- `Eternal_FE/Eternal/src/components/AISummary.js` - 요약

---

## ✨ 완료!

이제 Eternal_FE와 Eternal_SV가 완전히 통합되었습니다!
- ✅ AI 챗봇 실시간 대화
- ✅ RAG 기반 데이터 검색
- ✅ 자동 차트 생성
- ✅ AI 요약 생성

질문이나 문제가 있으면 언제든 물어보세요! 🚀
