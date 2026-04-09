# ─── HuggingFace Spaces Dockerfile ───────────────────────────────────────────
# Serves the FastAPI backend. HF Spaces requires port 7860.

FROM python:3.11.11-slim

# HF Spaces runs containers as a non-root user (uid 1000).
# Create the user and workspace up front.
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install system dependencies needed by faiss-cpu / psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to non-root user (required by HF Spaces)
USER appuser

# HuggingFace Spaces always uses port 7860
EXPOSE 7860

# Start FastAPI via uvicorn
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "7860"]
