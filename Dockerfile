FROM public.ecr.aws/docker/library/python:3.12-slim

ARG API_PORT=8080
ARG APP_VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=${API_PORT} \
    APP_VERSION=${APP_VERSION}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/__init__.py ./src/__init__.py
COPY src/gwr_codes.py ./src/gwr_codes.py
COPY src/api ./src/api
COPY src/shared ./src/shared

EXPOSE ${API_PORT}

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -fsS http://localhost:${API_PORT}/health || exit 1

CMD ["python", "-m", "src.api.web_service"]
