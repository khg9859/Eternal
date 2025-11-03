# 📘 데이터 구성 및 실행 가이드

## 📂 데이터 구성 및 테이블 설명

| **데이터 계열** | **구성 테이블** | **설명** |
|------------------|------------------|-----------|
| **qpoll 계열** | `metadata`, `respondents`, `answers` | 인구통계 정보(`metadata`) + 응답 내용(`answers`) 모두 존재.<br>`respondents`는 패널 ID(`mb_sn`)와 벡터 저장용으로 사용. |
| **welcom_1st** | `respondents`, `metadata` | 지역·나이 등 기본 속성만 존재 → 별도의 `answers` 불필요.<br>`respondents`로 식별, `metadata`에 응답 내용 저장.<br>(1st의 응답내용 = `metadata`) |
| **welcom_2nd** | `respondents`, `answers` | 문항 중심 응답 데이터만 존재 → `metadata` 없이 `answers`로 관리. |
| **공통 문항 정보** | `codebooks` | 모든 파일의 문항(`Q1~Qn`)과 보기 정보를 통합 관리.<br>`answers`와 `question_id` 기준으로 연결. |

---

## 🧱 테이블 구조

| **테이블명** | **컬럼명** | **설명** |
|---------------|-------------|-----------|
| `respondents` | `mb_sn`, `profile_vector` | 고유 패널 번호(`mb_sn`), 프로필 벡터(`p_vector`) |
| `answers` | `answer_id`, `mb_sn`, `question_id`, `answer_value`, `a_vector` | 응답 식별자, 응답자 번호, 코드북 내 문항 번호, 답변값, 답변 임베딩 |
| `metadata` | `metadata_id`, `mb_sn`, `mobile_carrier`, `gender`, `age`, `region` | 인구통계 메타데이터 (이동통신사, 성별, 연령, 지역 등) |
| `codebooks` | `codebook_id`, `codebook_data (jsonb)`, `q_vector` | 코드북 파일 ID, 문항 내용(JSON 형식), 문항 임베딩 벡터 |

---

## ⚙️ 코드 실행 순서

> ⚠️ *requirements.txt의 모든 파이썬 라이브러리가 이미 설치되어 있다고 가정합니다.*

---

### 1️⃣ 데이터 파일 준비

#### 🧩 Qpoll 계열
- 데이터 경로:  ./Data/db_insert/panelData/
- 필요한 `.xlsx` 파일을 아래 폴더로 복사:./Data/db_insert/execptFile/


#### 🧩 Welcom 1st / 2nd 계열
- 위와 동일하게 실행  
- 단, **파일 확장자는 `.csv`**  
- 코드북(`codebook_*.xlsx` 등)이 있다면 함께 복사해야 함  

---

### 2️⃣ 데이터 삽입 코드 수정

| **파일명** | **수정 항목** |
|-------------|---------------|
| `insert_1st.py`, `insert_2nd.py` | 데이터 파일 경로 및 파일명, DB 설정값 |
| `insert2db2.py` | 실행 경로 기준으로 파일 경로 및 DB 설정값 수정 |

---

### 3️⃣ 데이터 삽입 실행

```bash
python ./Data/db_insert/insert_all.py

4️⃣ 임베딩 실행
python ./embedding/embedding.py
python ./embedding/profileVector.py

5️⃣ PostgreSQL 검수

psql 환경에서 데이터가 정상적으로 삽입되고
임베딩(p_vector, a_vector, q_vector)이 잘 생성되었는지 확인합니다.

✅ 요약 실행 플로우
# 1. 데이터 준비
cp ./execptFile/*.xlsx ./Data/db_insert/panelData/

# 2. 경로 및 DB 설정 수정
# 3. 데이터 삽입
python ./Data/db_insert/insert_all.py

# 4. 임베딩 실행
python ./embedding/embedding.py
python ./embedding/profileVector.py

# 5. DB 검수 (psql)
