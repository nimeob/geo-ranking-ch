FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY src/__init__.py ./src/__init__.py
COPY src/gwr_codes.py ./src/gwr_codes.py
COPY src/api ./src/api
COPY src/compliance ./src/compliance
COPY src/shared ./src/shared

EXPOSE 8080

CMD ["python", "-m", "src.api.web_service"]
