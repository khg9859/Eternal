# DataSearch - 자연어 검색 시스템

구글과 유사한 UI를 가진 CSV/Excel 파일을 JSON으로 변환하고 자연어로 검색할 수 있는 웹 애플리케이션입니다.

<div align=center><h1>📚 STACKS</h1></div>

<div align=center> 
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=React&logoColor=black">
  <img src="https://img.shields.io/badge/TailwindCSS-06B6D4?style=for-the-badge&logo=Tailwindcss&logoColor=white">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=JavaScript&logoColor=black">
    <br>
  <img src="https://img.shields.io/badge/github-181717?style=for-the-badge&logo=github&logoColor=white">
  <img src="https://img.shields.io/badge/git-F05032?style=for-the-badge&logo=git&logoColor=white">
  <br>
</div>

## 주요 기능

- 🔍 구글 스타일의 검색 인터페이스
- 📁 CSV/Excel 파일 드래그 앤 드롭 업로드 (.csv, .xlsx, .xls)
- 🔄 CSV/Excel to JSON 자동 변환
- 🗣️ 자연어 검색 (향후 구현 예정)
- 📊 검색 결과 미리보기
- 📱 반응형 디자인

## 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 개발 서버 실행
```bash
npm start
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 열어 확인하세요.

## 사용 방법

1. **파일 업로드**: 메인 페이지에서 CSV 또는 Excel 파일을 드래그하거나 클릭하여 업로드
2. **자연어 검색**: 업로드 완료 후 검색박스에 자연어로 질문 입력
3. **결과 확인**: 검색 결과를 JSON 형태로 미리보기 및 다운로드

## 지원 파일 형식

- **CSV**: .csv
- **Excel**: .xlsx, .xls
