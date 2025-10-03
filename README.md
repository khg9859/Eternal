# ❄️ 에테르넬 (Eternel)

> **25-2 캡스톤디자인 | 자연어 질의 기반 추출 아키텍처**  
> 자연어 검색 → 데이터 추출 → 시각화까지 이어지는 웹 서비스

---

## 📌 프로젝트 소개

에테르넬은 **자연어 질의 기반 데이터 추출 및 시각화 플랫폼**입니다.  
사용자는 자연어로 데이터를 검색하고, 결과를 **표·차트·대시보드** 형태로 확인할 수 있습니다.

---

## 🧰 기술 스택

| 영역         | 스택                                                                                                                                                                                     |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Frontend** | <img src="https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=white"/> <img src="https://img.shields.io/badge/TailwindCSS-38B2AC?logo=tailwindcss&logoColor=white"/>          |
| **Backend**  | <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white"/> <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white"/>                |
| **Database** | <img src="https://img.shields.io/badge/PostgreSQL-336791?logo=postgresql&logoColor=white"/>                                                                                              |
| **Infra**    | <img src="https://img.shields.io/badge/AWS-232F3E?logo=amazonaws&logoColor=white"/> <img src="https://img.shields.io/badge/GitHub%20Actions-2088FF?logo=githubactions&logoColor=white"/> |
| **LLM**      | OpenAI API / 프롬프트 엔지니어링                                                                                                                                                         |

---

## 👥 팀 역할

| 👤 이름  | 🛠️ 역할            | 📌 주요 담당                                             |
| -------- | ------------------ | -------------------------------------------------------- |
| **홍근** | 🧭 팀장 / PM       | 일정 관리 · 주간 보고서 취합 · GitHub 관리 · 발표/브리핑 |
| **용주** | 🎨 프론트엔드      | React + Tailwind UI 제작 · 시각화 · UX 최적화            |
| **정원** | 📊 데이터 엔지니어 | 데이터 전처리 · 스키마 설계 · 임베딩 · PostgreSQL        |
| **민석** | 🤖 LLM 엔지니어    | LLM API 연동 · 프롬프트 설계 · RAG/Eval 관리             |
| **범창** | ⚙️ 백엔드          | FastAPI 서버 · DB 연동 · AWS 배포                        |

---

## 🧭 Git 명령어 치트시트

| 명령어                       | 설명                          |
| ---------------------------- | ----------------------------- |
| `git clone <url>`            | 원격 저장소 복제              |
| `git add .`                  | 전체 변경 스테이징            |
| `git add <파일>`             | 특정 파일 스테이징            |
| `git commit -m "메시지"`     | 메시지와 함께 커밋            |
| `git log`                    | 커밋 히스토리 확인            |
| `git branch`                 | 브랜치 목록 확인              |
| `git checkout <브랜치명>`    | 해당 브랜치 이동              |
| `git checkout -b <브랜치명>` | 새 브랜치 생성 + 이동         |
| `git push origin <브랜치명>` | 원격 브랜치로 푸시            |
| `git pull origin main`       | 원격 `main` 가져오기(병합)    |
| `git fetch --all --prune`    | 원격 브랜치 최신화(삭제 포함) |

---

## 🌿 Git 브랜치 전략

### 기본 브랜치

| 브랜치    | 역할                                                       |
| --------- | ---------------------------------------------------------- |
| `main`    | **최종 배포 브랜치** (보호됨, 직접 푸시 ❌)                |
| `dev`     | **개발 통합 브랜치** (모든 기능 브랜치는 여기로 먼저 머지) |
| `feature` | 기능 개발 브랜치                                           |
| `fix`     | 버그 수정 브랜치                                           |
| `hotfix`  | 긴급 수정 (main에서 바로 분기)                             |

### 규칙

- `main` 은 **되도록 직접 건드리지 않는다** → 반드시 **PR + 리뷰** 필요
- 모든 브랜치는 **이슈 번호 기반 네이밍** :
  - 예) `feat/#12-search-api`, `fix/#42-db-connection`
- 커밋 메시지 컨벤션:
  - `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`
- PR 시 체크리스트:
  - [ ] 관련 이슈 링크
  - [ ] 변경 내용 요약
  - [ ] 스크린샷/예시 포함
  - [ ] 리뷰어 승인 ✅

---

📢 **Note**

- 상세 규칙(API 계약, ERD, Definition of Done 등)은 `/docs` 디렉토리 참고.
