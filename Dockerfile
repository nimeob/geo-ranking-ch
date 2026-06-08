FROM public.ecr.aws/docker/library/python:3.12.2-slim

# Erstelle nicht-privilegierten Benutzer
RUN groupadd -r appuser && useradd -r -g appuser appuser

ARG API_PORT=8080
ARG APP_VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PORT=${API_PORT} \\
    APP_VERSION=${APP_VERSION}

WORKDIR /app

# Systemabhaengigkeiten
RUN apt-get update && \\
    apt-get install -y --no-install-recommends curl && \\
    rm -rf /var/lib/apt/lists/*

# Python-Abhaengigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode (mit korrekten Berechtigungen)
COPY --chown=appuser:appuser src/ ./src/

# Wechsel zu nicht-privilegiertem Benutzer
USER appuser

EXPOSE ${API_PORT}

# Verbesserte Healthcheck mit Timeout
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD curl -fsS --max-time 5 http://localhost:${API_PORT}/health || exit 1

CMD ["python", "-m", "src.api.web_service"]