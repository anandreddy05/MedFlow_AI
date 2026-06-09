# ---------- Builder ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .

# Force CPU-only torch
RUN pip install --no-cache-dir \
    torch==2.12.0 \
    torchvision==0.27.0 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    --upgrade-strategy only-if-needed \
    -r requirements-prod.txt


# ---------- Runtime ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FASTEMBED_CACHE_DIR=/app/models
ENV TORCH_HOME=/app/models

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN mkdir -p /app/models

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]