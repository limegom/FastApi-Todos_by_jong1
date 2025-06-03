# 1) Python 3.13-slim 베이스 이미지
FROM python:3.13-slim

# 2) 작업 디렉토리 설정
WORKDIR /app

# 3) 먼저 requirements.txt만 복사하여 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) 나머지 소스 코드를 복사
COPY . .

# 5) 기본 Loki 엔드포인트 환경 변수
ENV LOKI_ENDPOINT=http://loki:3100/loki/api/v1/push

# 6) FastAPI 서버 실행 커맨드
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
