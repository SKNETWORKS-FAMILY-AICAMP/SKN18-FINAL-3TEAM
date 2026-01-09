FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
# uv 설치 후 requirements 설치 (빌드 속도 개선)
RUN curl -Ls https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv pip install --system --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend/video_pipeline /app/frontend/video_pipeline
COPY backend/django/entrypoint.sh /app/entrypoint.sh
COPY infra/database/init.sql /app/init.sql
RUN chmod +x /app/entrypoint.sh

# 작업 디렉토리가 /app/backend/django 라면 경로에 주의하세요
WORKDIR /app/backend/django

# ENTRYPOINT는 반드시 리스트 형태로 작성
ENTRYPOINT ["/app/entrypoint.sh"]

# 기본 실행 명령 (ECS에서 override 하지 않을 경우)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
