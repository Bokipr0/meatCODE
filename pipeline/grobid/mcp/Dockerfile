# Last updated: 2026-10-20 · Codex / Full-Stack · small SDK-backed GROBID adapter.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "mcp==1.26.0"
COPY core.py server.py /app/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    GROBID_URL=http://host.docker.internal:8070 PDF_ROOT=/pdfs OUTPUT_ROOT=/outputs
ENTRYPOINT ["python", "/app/server.py"]
