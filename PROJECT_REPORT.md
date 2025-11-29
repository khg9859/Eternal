# DataSearch - 자연어 데이터 검색 시스템

## 프로젝트 개요
CSV/Excel 파일을 JSON으로 변환하고 자연어로 검색할 수 있는 Google 스타일 웹 애플리케이션

## 기술 스택
- **Frontend**: React 18, Tailwind CSS, JavaScript ES6+
- **라이브러리**: XLSX (Excel 파일 처리)
- **디자인**: Material Design, Glassmorphism 효과

## 주요 기능
1. **파일 업로드**: CSV, XLSX, XLS 지원, 드래그 앤 드롭
2. **자연어 검색**: Google 스타일 검색박스, AI 아이콘
3. **스마트 태그**: 8개 인기 검색어, 원클릭 검색
4. **검색 결과**: JSON 미리보기, 페이지네이션

## UI/UX 특징
- **커스텀 SVG 로고**: 그라데이션 텍스트, 데이터 아이콘
- **글래스모피즘**: 반투명 배경, 블러 효과
- **반응형 디자인**: 모바일 우선 접근
- **Google 컬러**: 브랜드 컬러 팔레트 적용

## 핵심 구현
```javascript
// 파일 처리 통합 로직
const handleFile = (file) => {
  const isCSV = file.name.endsWith('.csv');
  const isXLSX = file.name.endsWith('.xlsx');
  // CSV/Excel 자동 파싱 및 JSON 변환
};
```

## 성과
- **개발 시간**: 8시간
- **컴포넌트**: 7개 모듈화
- **파일 지원**: 3개 형식
- **사용자 경험**: Google 수준 UI/UX

## 향후 계획
- 실제 AI 자연어 처리 엔진 통합
- 백엔드 API 서버 구축
- 데이터 시각화 차트 추가
- PWA 변환

## 실행 방법
```bash
npm install
npm start
```

## 결론
모던 웹 기술을 활용하여 직관적이고 실용적인 데이터 검색 도구를 구현했으며, AI 기반 데이터 분석 플랫폼으로 확장 가능한 견고한 기반을 마련했습니다.