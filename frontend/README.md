# Frontend - React Application

자연어 검색 및 데이터 시각화를 위한 React 프론트엔드

## 기술 스택

- **React 18**: UI 라이브러리
- **TailwindCSS**: 유틸리티 기반 CSS 프레임워크
- **Chart.js & react-chartjs-2**: 데이터 시각화
- **Framer Motion**: 애니메이션
- **React Router**: 라우팅
- **html2canvas & jspdf**: PDF/이미지 내보내기

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/          # 재사용 가능한 UI 컴포넌트
│   │   ├── AIChatInterface.js
│   │   ├── AISummary.js
│   │   ├── ChartSection.js
│   │   ├── DashboardHeader.js
│   │   ├── DataTable.js
│   │   ├── Logo.js
│   │   ├── QuickStats.js
│   │   └── SidePanel.js
│   ├── pages/               # 페이지 컴포넌트
│   │   ├── HomePage.js
│   │   └── ResultsPage.js
│   ├── App.js               # 메인 앱 컴포넌트
│   ├── index.js             # React 진입점
│   └── index.css            # 전역 스타일
├── public/                  # 정적 파일
│   ├── index.html
│   ├── bg.mp4              # 배경 비디오 (gitignore)
│   └── bg1.mp4             # 배경 비디오 (gitignore)
├── package.json
├── tailwind.config.js
└── postcss.config.js
```

## 설치 및 실행

### 1. 의존성 설치

```bash
npm install
```

### 2. 개발 서버 실행

```bash
npm start
```

애플리케이션이 http://localhost:3000 에서 실행됩니다.

### 3. 프로덕션 빌드

```bash
npm run build
```

빌드된 파일은 `build/` 디렉토리에 생성됩니다.

## 주요 컴포넌트

### Pages

- **HomePage**: 검색 인터페이스 및 메인 페이지
- **ResultsPage**: 검색 결과 및 데이터 시각화 페이지

### Components

- **AIChatInterface**: AI 챗봇 인터페이스
- **AISummary**: AI 요약 분석 결과 표시
- **ChartSection**: 다양한 차트 렌더링
- **DashboardHeader**: 대시보드 헤더
- **DataTable**: 페이지네이션 가능한 데이터 테이블
- **QuickStats**: 주요 통계 카드
- **SidePanel**: 필터링 사이드 패널
- **Logo**: 애플리케이션 로고

## 환경 설정

백엔드 API 연결을 위해 API 엔드포인트를 설정하세요:

```javascript
const API_URL = 'http://localhost:8000';
```

## 스크립트

- `npm start`: 개발 서버 실행
- `npm run build`: 프로덕션 빌드
- `npm test`: 테스트 실행
- `npm run eject`: React 설정 추출 (되돌릴 수 없음)
