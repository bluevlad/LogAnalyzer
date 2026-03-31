# LogAnalyzer

Docker 컨테이너 로그를 수집·분석하여 Request 패턴 분석, 오류 감지, 자동 연동을 수행하는 서비스.

## Quick Start

```bash
# 1. DB/계정 생성 (DB_ACCOUNT_POLICY 기준 — 실제 비밀번호는 ENVIRONMENT_STANDARD.md 참조)
docker exec -it postgresql psql -U postgres -c "CREATE DATABASE loganalyzer;"
docker exec -it postgresql psql -U postgres -c "CREATE DATABASE loganalyzer_dev;"
docker exec -it postgresql psql -U postgres -c "CREATE USER loganalyzer_svc WITH PASSWORD '<PASSWORD>';"
docker exec -it postgresql psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE loganalyzer TO loganalyzer_svc;"

# 2. 환경변수 (.env.example 복사 후 실제 값 입력)
cp .env.example .env
# vi .env  ← 비밀번호, API 키 등 설정

# 3. 실행
docker-compose up -d --build
```

- Backend: http://localhost:9092/api/docs
- Frontend: http://localhost:4092

## Tech Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, APScheduler, Docker SDK
- Frontend: React 18, TypeScript, Ant Design 5, Recharts
- Database: PostgreSQL 15

## Features

- 5분 주기 Docker 로그 수집 (24개 컨테이너)
- HTTP 요청 분석 (Nginx/Uvicorn/Spring Boot 로그 파싱)
- 오류 자동 분류 + Fingerprint 그룹핑
- GitHub Issue 자동 생성 (QA-AGENT-META 포함)
- QA Dashboard / StandUp 자동 연동
