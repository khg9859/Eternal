# 🌌 에테르넬 (Eternel)

> 2025-2 기업연계 SW 캡스톤디자인 — PMI × 한성대학교  
> 주제: **자연어 질의 기반 패널 데이터 추출 아키텍처 구성**

---

## 📖 프로젝트 소개
- 자연어 질의를 통해 대규모 패널 데이터에서 원하는 정보를 효율적으로 추출하는 시스템
- **데이터 수집 → 가공/저장 → 검색 → LLM 응답 → 시각화** 전 과정을 아우르는 아키텍처 설계
- 최종 결과물: 웹 기반 검색/조회 서비스 (프론트엔드 + 백엔드 + 데이터 파이프라인)

---

## 👥 팀 구성 & 역할
| 이름   | 역할            | 주요 업무                                                         |
| ------ | --------------- | ---------------------------------------------------------------- |
| 팀장   | 기획/관리        | 일정 관리, 대외 커뮤니케이션, 최종 산출물 총괄                   |
| 홍근   | 부팀장/백엔드    | API 서버, DB 설계, GitHub 운영                                   |
| ○○○   | 프론트엔드       | UI/UX 설계 및 구현 (React), 데이터 시각화                         |
| ○○○   | 데이터 담당      | 데이터 가공/정제, 샘플 DB 구축, 스키마 관리                       |
| ○○○   | LLM 담당         | 모델 프롬프트 설계, API 연동, 검색어 증강                         |
| ○○○   | 테스트/문서화    | 테스트 코드 작성, 보고서/README/발표자료 정리                    |

---

## 🔀 브랜치 전략
- **main**  
  - 항상 배포 가능한 상태 유지 (직접 push 금지, PR만 머지 가능)
- **feature/**  
  - 새로운 기능 개발 시 사용  
  - 규칙: `feature/{이슈번호}-{기능명}`  
  - 예시: `feature/1-login`, `feature/3-search-api`
- **fix/**  
  - 버그 수정 브랜치  
  - 예시: `fix/5-auth-bug`
- **docs/**  
  - 문서/README/발표자료 수정
- **hotfix/**  
  - 배포 중 긴급 수정

---

## 📝 커밋 메시지 규칙
- 형식: `[타입/#이슈번호] - 작업 내용`
- 타입 예시:
  - `feat` : 새로운 기능
  - `fix`  : 버그 수정
  - `docs` : 문서 수정
  - `refactor` : 리팩토링
  - `chore` : 기타 설정 변경
- 예시:
  - `[feat/#1] - 로그인 페이지 추가`
  - `[fix/#2] - DB 연결 버그 수정`

---

## ⚙️ 협업 규칙
1. 모든 작업은 **이슈 생성 → 브랜치 생성 → PR → 리뷰 → 머지** 순서로 진행  
2. **작업 단위는 작게**: 100~300줄 정도, PR은 자주 올리기  
3. **코드 리뷰 필수**: 최소 1명 이상 승인 후 머지  
4. **.env, 민감 데이터 푸시 금지**  
5. **README/Docs 최신화**: 실행 방법, 데이터 구조, API 변경사항은 항상 기록  

---

## 🚀 실행 방법 (예시)
```bash
# 프론트엔드
cd frontend
npm install
npm run dev

# 백엔드 (FastAPI)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

<div align=center><h1>📚 STACKS</h1></div>

<div align=center> 
  <img src="https://img.shields.io/badge/claude-E34F26?style=for-the-badge&logo=claude&logoColor=white">
<img src="https://img.shields.io/badge/TailwindCss-181717?style=for-the-badge&logo=Tailwindcss&logoColor=white">
<img src="https://img.shields.io/badge/React-3776AB?style=for-the-badge&logo=React&logoColor=white">
    <br>
  <img src="https://img.shields.io/badge/github-181717?style=for-the-badge&logo=github&logoColor=white">
  <img src="https://img.shields.io/badge/git-F05032?style=for-the-badge&logo=git&logoColor=white">
  <br>
</div>
