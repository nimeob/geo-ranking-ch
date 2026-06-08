FROM public.ecr.aws/docker/library/python:3.12-slim

# Erstelle nicht-privilegierten Benutzer und Gruppe
RUN groupadd -r appuser && useradd -r -g appuser appuser

ARG API_PORT=8080
ARG APP_VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1 \\ PYTHONUNBUFFERED=1 \\ PORT=${API_PORT} \\ APP_VERSION=${APP_VERSION}

WORKDIR /app

# Systemabhaengigkeiten
RUN apt-get update && \\
    apt-get install -y --no-install-recommends curl && \\
    rm -rf /var/lib/apt/lists/*

# Individuelle Dateien kopieren (wie vom Test erwartet)
COPY requirements.txt ./requirements.txt
COPY src/__init__.py ./src/__init__.py
COPY src/_legacy_module_proxy.py ./src/_legacy_module_proxy.py
COPY src/gwr_codes.py ./src/gwr_codes.py
COPY src/api ./src/api
COPY src/compliance ./src/compliance
COPY src/shared ./src/shared

RUN pip install --no-cache-dir -r requirements.txt

# Berechtigungen setzen
RUN chown -R appuser:appuser /app/src /app/requirements.txt

# Wechsel zu nicht-privilegiertem Benutzer
USER appuser

EXPOSE ${API_PORT}

# Verbesserte Healthcheck mit Timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD curl -fsS --max-time 5 http://localhost:${API_PORT}/health || exit 1

CMD ["python", "-m", "src.api.web_service"]