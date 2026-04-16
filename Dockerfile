# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libxml2-dev libxslt-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# Install minimal TeX for PDF generation (no Ollama — use Groq API instead)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/ backend/
COPY agents/ agents/
COPY src/ src/
COPY models/ models/
COPY mlops/ mlops/
COPY main.py requirements.txt ./

RUN mkdir -p outputs logs

# Render injects $PORT at runtime; default to 8000 for local use
ENV PORT=8000
ENV MODEL_PROVIDER=groq

EXPOSE 8000

# Use shell form so $PORT is expanded at runtime
CMD ["sh", "-c", "python -m uvicorn backend.api:app --host 0.0.0.0 --port ${PORT}"]
