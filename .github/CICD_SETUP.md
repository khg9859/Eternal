# CI/CD 설정 가이드

이 문서는 Eternal 프로젝트의 GitHub Actions CI/CD 파이프라인 설정 방법을 안내합니다.

## 📋 목차

1. [개요](#개요)
2. [필수 준비사항](#필수-준비사항)
3. [GitHub Secrets 설정](#github-secrets-설정)
4. [Docker Hub 설정](#docker-hub-설정)
5. [EC2 서버 설정](#ec2-서버-설정)
6. [워크플로우 설명](#워크플로우-설명)
7. [트러블슈팅](#트러블슈팅)

---

## 개요

### CI/CD 파이프라인 구성

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend CI                    Backend CI/CD               │
│  ├── Lint & Build              ├── Test                    │
│  ├── Run Tests                 ├── Build Docker Image      │
│  └── Upload Artifacts          ├── Push to Docker Hub      │
│                                 └── Deploy to EC2           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 워크플로우 트리거

- **Frontend CI**: `frontend/` 디렉토리 변경 시 실행
- **Backend CI/CD**: `backend/` 디렉토리 변경 시 실행 + main 브랜치에 push 시 배포

---

## 필수 준비사항

### 1. Docker Hub 계정
- [Docker Hub](https://hub.docker.com/) 계정 생성
- Access Token 생성 필요

### 2. AWS EC2 인스턴스
- Ubuntu/Amazon Linux 서버
- Docker 및 Docker Compose 설치됨
- SSH 접근 가능

### 3. GitHub 저장소
- Admin 권한 필요 (Secrets 설정을 위해)

---

## GitHub Secrets 설정

GitHub 저장소의 Settings > Secrets and variables > Actions로 이동하여 다음 secrets를 추가하세요.

### 필수 Secrets

| Secret 이름 | 설명 | 예시 |
|-------------|------|------|
| `DOCKER_USERNAME` | Docker Hub 사용자명 | `myusername` |
| `DOCKER_PASSWORD` | Docker Hub Access Token | `dckr_pat_xxx...` |
| `EC2_HOST` | EC2 인스턴스 IP 또는 도메인 | `1.2.3.4` 또는 `ec2-xxx.compute.amazonaws.com` |
| `EC2_USER` | EC2 SSH 사용자명 | `ubuntu` 또는 `ec2-user` |
| `EC2_SSH_KEY` | EC2 SSH Private Key | `-----BEGIN RSA PRIVATE KEY-----...` |

### 선택적 Secrets

| Secret 이름 | 설명 | 기본값 |
|-------------|------|--------|
| `EC2_PORT` | SSH 포트 | `22` |
| `EC2_PROJECT_PATH` | 프로젝트 경로 | `~/eternel` |

---

## Docker Hub 설정

### 1. Access Token 생성

1. [Docker Hub](https://hub.docker.com/)에 로그인
2. Account Settings > Security > New Access Token
3. 토큰 이름 입력 (예: `github-actions`)
4. 권한: `Read, Write, Delete` 선택
5. 생성된 토큰을 복사하여 `DOCKER_PASSWORD` Secret에 저장

### 2. Repository 생성 (선택사항)

Docker Hub에서 `eternel-backend` 저장소를 미리 생성할 수 있습니다.
- 자동 생성되므로 필수는 아닙니다.

---

## EC2 서버 설정

### 1. Docker 설치

```bash
# Ubuntu
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Amazon Linux 2
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -aG docker ec2-user
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 프로젝트 디렉토리 설정

```bash
# 프로젝트 클론
cd ~
git clone https://github.com/khg9859/Eternal.git eternel
cd eternel

# .env 파일 설정
nano .env
# OPENAI_API_KEY, DATABASE_URL 등 환경변수 설정
```

### 3. SSH Key 설정

로컬에서 SSH 키 생성 (또는 기존 키 사용):

```bash
# 새 키 생성 (선택사항)
ssh-keygen -t rsa -b 4096 -C "github-actions"

# 공개키를 EC2에 추가
cat ~/.ssh/id_rsa.pub
# EC2의 ~/.ssh/authorized_keys에 추가
```

Private Key를 `EC2_SSH_KEY` Secret에 추가:

```bash
# Private Key 전체 내용 복사
cat ~/.ssh/id_rsa
# GitHub Secrets에 붙여넣기
```

### 4. 방화벽 설정

EC2 Security Group에서 다음 포트 허용:
- `22`: SSH
- `8000`: FastAPI (필요시)
- `3000`: React (필요시)

---

## 워크플로우 설명

### Frontend CI Workflow

**파일**: [`.github/workflows/frontend-ci.yml`](workflows/frontend-ci.yml)

**실행 조건**:
- `frontend/` 디렉토리 변경 시
- PR 생성 시
- main, develop 브랜치 push 시

**작업 내용**:
1. Node.js 18 설치
2. 의존성 설치 (`npm ci`)
3. ESLint 실행
4. 프로젝트 빌드
5. 테스트 실행
6. 빌드 결과물 아티팩트로 저장

### Backend CI/CD Workflow

**파일**: [`.github/workflows/backend-ci-cd.yml`](workflows/backend-ci-cd.yml)

**실행 조건**:
- `backend/` 디렉토리 변경 시
- main 브랜치 push 시 배포 실행

**작업 내용**:

#### Job 1: Test
1. Python 3.11 설치
2. 의존성 설치
3. Black 코드 포맷 체크
4. Flake8 린팅

#### Job 2: Build and Push (main 브랜치만)
1. Docker Buildx 설정
2. Docker Hub 로그인
3. Docker 이미지 빌드
4. Docker Hub에 푸시
   - `latest` 태그
   - 브랜치별 SHA 태그
5. 빌드 캐시 활용

#### Job 3: Deploy (main 브랜치만)
1. EC2에 SSH 연결
2. 최신 코드 pull
3. 최신 Docker 이미지 pull
4. 컨테이너 재시작
5. 구 이미지 정리

---

## 사용 방법

### 1. 일반 개발 플로우

```bash
# 1. 새 브랜치 생성
git checkout -b feature/new-feature

# 2. 코드 작성 및 커밋
git add .
git commit -m "feat: add new feature"

# 3. GitHub에 푸시
git push origin feature/new-feature

# 4. PR 생성
# GitHub에서 Pull Request 생성
# CI가 자동으로 실행됨

# 5. main에 머지 후 자동 배포
# main 브랜치에 머지되면 자동으로 배포됨
```

### 2. 로컬에서 Docker 테스트

```bash
# Backend Docker 이미지 빌드
cd backend
docker build -t eternel-backend:test .

# 컨테이너 실행
docker run -p 8000:8000 --env-file ../.env eternel-backend:test

# Docker Compose로 실행
docker-compose up
```

### 3. 수동 배포

필요시 EC2에서 수동으로 배포:

```bash
ssh user@ec2-instance
cd ~/eternel
git pull origin main
docker-compose down
docker-compose up -d --build
```

---

## 트러블슈팅

### 1. Docker Hub 푸시 실패

**증상**: `unauthorized: authentication required`

**해결**:
- `DOCKER_USERNAME`과 `DOCKER_PASSWORD` 확인
- Docker Hub Access Token 재생성
- Token 권한 확인 (Read, Write, Delete)

### 2. EC2 배포 실패

**증상**: SSH 연결 실패

**해결**:
- EC2 Security Group에서 SSH 포트(22) 허용 확인
- `EC2_HOST`, `EC2_USER` 확인
- `EC2_SSH_KEY`가 올바른지 확인 (전체 내용 포함)
- EC2의 `~/.ssh/authorized_keys`에 공개키 추가 확인

### 3. 환경변수 문제

**증상**: 배포 후 애플리케이션 오류

**해결**:
- EC2의 `.env` 파일 확인
- `docker-compose.yml`의 환경변수 설정 확인
- 컨테이너 로그 확인: `docker-compose logs -f`

### 4. 빌드 실패

**증���**: Frontend 빌드 실패

**해결**:
```bash
# 로컬에서 테스트
cd frontend
npm install
npm run build
```

**증상**: Backend 빌드 실패

**해결**:
```bash
# requirements.txt 확인
cd backend
pip install -r requirements.txt
```

### 5. 워크플로우가 실행되지 않음

**원인**:
- 변경사항이 `paths`에 해당하지 않음
- 워크플로우 파일 자체에 문법 오류

**해결**:
- GitHub Actions 탭에서 에러 확인
- YAML 문법 검증: [YAML Lint](http://www.yamllint.com/)

---

## 모니터링 및 로그

### GitHub Actions 확인

1. GitHub 저장소 > Actions 탭
2. 최근 워크플로우 실행 내역 확인
3. 각 Job의 로그 확인

### EC2 로그 확인

```bash
# Docker 컨테이너 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend

# 실행 중인 컨테이너 확인
docker-compose ps
```

---

## 추가 개선사항

### 1. Staging 환경 추가

`develop` 브랜치에 대한 별도 배포 환경:

```yaml
# .github/workflows/backend-ci-cd.yml에 추가
deploy-staging:
  if: github.ref == 'refs/heads/develop'
  # staging 서버로 배포
```

### 2. 슬랙 알림

배포 결과를 슬랙으로 알림:

```yaml
- name: Slack Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 3. 롤백 기능

이전 버전으로 롤백:

```bash
# EC2에서 이전 이미지로 롤백
docker-compose down
docker pull username/eternel-backend:previous-sha
docker-compose up -d
```

---

## 참고 자료

- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)
- [Docker Hub 문서](https://docs.docker.com/docker-hub/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)

---

## 지원

문제가 발생하면 이슈를 생성해주세요:
- GitHub Issues: https://github.com/khg9859/Eternal/issues
