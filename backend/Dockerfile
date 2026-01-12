FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
# uv 설치 후 requirements 설치 (빌드 속도 개선)
RUN curl -Ls https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv pip install --system --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY frontend/video_pipeline /app/frontend/video_pipeline
COPY backend/django/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
