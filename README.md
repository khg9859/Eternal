# Eternel

> **25-2 캡스톤디자인 | 자연어 질의 기반 데이터 추출 및 시각화 아키텍처**
> 최근 생성형 AI 기술은 다양한 분야에서 활용되고 있지만, 복잡한 패널 데이터를 일반 사용자가 직관적으로 검색하고 분석하는 데는 여전히 어려움이 있습니다.
> Eternel은 **자연어 질의를 통해 누구나 쉽게 패널 데이터를 검색**하고, **AI 기반 분석 결과를 시각화**하여 데이터 인사이트를 발견할 수 있도록 돕는 플랫폼입니다.

![Eternel 메인 화면](images/리드미.png)

---

## 주요 기능

### 1. 자연어 기반 스마트 검색
사용자는 "체력 관리", "결혼 상태" 등 일상적인 언어로 질문하면, AI가 관련 패널 데이터를 자동으로 검색하여 결과를 제공합니다.

### 2. 다양한 데이터 시각화
- **기본 차트**: 검색 결과를 막대, 선형, 파이 차트로 시각화
- **고급 차트**: 여러 차트를 동시에 표시하거나 개별 선택 가능
- **데이터 테이블**: 정렬, 페이지네이션, 통계 요약 기능 제공
- **상세 결과**: 검색 결과의 세부 정보 확인

### 3. 스마트 필터링
카테고리, 지역, 나이별 동적 필터를 적용하여 원하는 데이터를 정밀하게 추출할 수 있습니다.

### 4. AI 채팅 인터페이스
검색창 클릭으로 활성화되는 AI 어시스턴트를 통해 데이터에 대한 자유로운 질문이 가능하며, 이전 대화 맥락을 유지하여 연속적인 질의응답을 지원합니다.

### 5. 데이터 내보내기
차트 이미지, PDF, CSV 형식으로 분석 결과를 다운로드할 수 있습니다.

---

## 기술 스택

| 영역         | 스택                                                                                                                                                                                     |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Frontend** | <img src="https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=white"/> <img src="https://img.shields.io/badge/TailwindCSS-38B2AC?logo=tailwindcss&logoColor=white"/> <img src="https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white"/> |
| **Backend**  | <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white"/> <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white"/> <img src="https://img.shields.io/badge/LangChain-121212?logo=chainlink&logoColor=white"/> |
| **Database** | <img src="https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white"/> <img src="https://img.shields.io/badge/pgvector-336791?logo=postgresql&logoColor=white"/> |
| **Infra**    | <img src="https://img.shields.io/badge/AWS-232F3E?logo=amazonaws&logoColor=white"/> <img src="https://img.shields.io/badge/EC2-FF9900?logo=amazonec2&logoColor=white"/> |
| **LLM**      | OpenAI API · 프롬프트 엔지니어링 · RAG |

---

## 시스템 아키텍처

```
사용자 질의 (자연어)
   ↓
React Frontend (검색 UI)
   ↓
FastAPI Backend
   ↓
┌─────────────────────────────────┐
│  1. LangChain RAG Pipeline      │
│  2. PostgreSQL + pgvector       │
│  3. 임베딩 기반 유사도 검색      │
└─────────────────────────────────┘
   ↓
LLM (GPT) 응답 생성
   ↓
데이터 시각화 (Chart.js)
   ↓
사용자에게 결과 반환
```

---

## 프로젝트 구조

```
Eternal/
├── Front_test/              # React 프론트엔드
│   ├── src/
│   │   ├── components/      # UI 컴포넌트
│   │   │   ├── AIChatInterface.js
│   │   │   ├── AISummary.js
│   │   │   ├── ChartSection.js
│   │   │   ├── DataTable.js
│   │   │   └── QuickStats.js
│   │   ├── pages/
│   │   │   ├── HomePage.js
│   │   │   └── ResultsPage.js
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   └── package.json
│
├── Data/                    # 백엔드 및 데이터
│   ├── backend/
│   │   ├── main.py          # FastAPI 서버
│   │   ├── rag/             # RAG 파이프라인
│   │   └── database/        # DB 연결
│   └── requirements.txt
│
└── README.md
```

---

## 설치 및 실행

### 1. 프로젝트 클론
```bash
git clone -b FrontEnd https://github.com/khg9859/Eternal.git
cd Eternal
```

### 2. 프론트엔드 설정 및 실행
```bash
cd Front_test
npm install
npm start
```
애플리케이션이 http://localhost:3000 에서 실행됩니다.

### 3. 백엔드 설정 및 실행
```bash
cd Data/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
REACT_APP_API_BASE_URL=http://localhost:8000
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/eternel
```

### 참고사항
- 백엔드 실행 시 임베딩 모델 로딩으로 인해 30초 정도 소요됩니다.
- ESLint 경고는 백엔드 RAG 연동 후 자동으로 해결됩니다.

---

## 데이터 소스

### 패널 데이터
- **총 질문 수**: 452개
- **총 답변 수**: 115개
- **응답자 수**: 6명
- **데이터 출처**: Welcome 1차/2차 설문조사

### 검색 가능한 주제
- 체력 관리 및 건강
- 결혼 상태 및 가족 관계
- 나이 및 연령대별 분석
- 지역별 특성
- 직업 및 교육 수준
- 생활 만족도

---

## 팀 역할

| 이름     | 역할                | 주요 담당                                                |
| -------- | ------------------- | -------------------------------------------------------- |
| **홍근** | 팀장 / PM           | 일정 관리 · 주간 보고서 취합 · GitHub 관리 · 발표/브리핑 |
| **용주** | 프론트엔드          | React + Tailwind UI 제작 · 시각화 · UX 최적화            |
| **정원** | 데이터 엔지니어     | 데이터 전처리 · 스키마 설계 · 임베딩 · PostgreSQL        |
| **민석** | LLM 엔지니어        | LLM API 연동 · 프롬프트 설계 · RAG/Eval 관리             |
| **범창** | 백엔드              | FastAPI 서버 · DB 연동 · AWS 배포                        |

---

## 주요 특징

### UI/UX
- **사이버펑크 디자인**: 어두운 배경과 네온 글로우 효과
- **노트북 목업**: 실제 노트북 화면 같은 3D 효과
- **부드러운 애니메이션**: 호버 효과와 전환 애니메이션
- **반응형 디자인**: 모바일/태블릿/데스크톱 지원

### 성능 최적화
- **지연 로딩**: 컴포넌트별 필요 시점 로딩
- **상태 관리**: React Hooks를 활용한 효율적 상태 관리
- **API 캐싱**: 검색 결과 캐싱으로 성능 향상

### 확장성
- **모듈화된 컴포넌트**: 재사용 가능한 컴포넌트 구조
- **API 추상화**: 백엔드 변경에 유연한 대응
- **테마 시스템**: 쉬운 디자인 변경 가능

---

## 향후 계획

### 단기 목표
- LLM API 연동으로 데이터 분석 고도화
- 실시간 데이터 업데이트 기능
- 사용자 맞춤형 대시보드

### 장기 목표
- 고급 통계 분석 기��
- 데이터 시각화 템플릿 확장
- 다국어 지원 (한국어/영어)

---

## Git 브랜치 전략

### 기본 브랜치

| 브랜치    | 역할                                                       |
| --------- | ---------------------------------------------------------- |
| `main`    | 최종 배포 브랜치 (보호됨, 직접 푸시 금지)                  |
| `dev`     | 개발 통합 브랜치 (모든 기능 브랜치는 여기로 먼저 머지)     |
| `feature` | 기능 개발 브랜치                                           |
| `fix`     | 버그 수정 브랜치                                           |

### 커밋 컨벤션
- `feat:` 새로운 기능 추가
- `fix:` 버그 수정
- `docs:` 문서 수정
- `refactor:` 코드 리팩토링
- `chore:` 빌드, 설정 파일 수정
- `test:` 테스트 코드 추가/수정

---

## 시연
[시연영상 보러가기](https://youtu.be/uSY6rJm9rxY)

---

**Eternel** - 데이터를 통한 인사이트 발견의 새로운 경험
