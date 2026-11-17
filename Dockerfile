# Lightweight CPU-optimized Docker image for Hugging Face Spaces & Render
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CROP_ADVISORY_DB=/tmp/crop_advisory.db

# Install CPU-only PyTorch & Torchvision first (~180 MB instead of ~2.5 GB CUDA wheels)
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY README.md ./

# Default port 7860 for Hugging Face Spaces; respects $PORT on Render/Railway
EXPOSE 7860

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
