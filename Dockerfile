# Dockerfile für geo-ranking-ch (FastAPI + UI)
FROM public.ecr.aws/docker/library/python:3.12-slim as builder

# Abhängigkeiten installieren
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Quelle kopieren
COPY . .

# Runtime-Image
FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app

# Benutzer erstellen
RUN useradd --create-home --shell /bin/bash appuser

# Curl für ECS-Healthchecks installieren
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten kopieren
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /app /app

# UI-Dateien kopieren
COPY --from=builder /app/ui /app/ui

# Umgebungsvariablen
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Port freigeben
EXPOSE 8000

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/health || exit 1

# als Nicht-Root-Benutzer ausführen
USER appuser

# Befehl zum Starten
CMD ["uvicorn", "src.api.web_service.main:app", "--host", "0.0.0.0", "--port", "8000"]