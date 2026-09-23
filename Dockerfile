# ─── Stage 1: System dependencies + Python packages ──────────────────────────
FROM python:3.11-slim

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install system libraries required by the Python packages:
#   libzbar0      — pyzbar (barcode decoding)
#   libgl1        — OpenCV (headless still needs libGL at runtime on some distros)
#   libglib2.0-0  — OpenCV (libgthread dependency)
#   libgomp1      — PyTorch OpenMP threading
#   libsm6        — OpenCV (some distros need this for headless mode)
#   libxext6      — OpenCV
#   libxrender1   — OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── Install Python dependencies ──────────────────────────────────────────────
# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir \
    && pip install --no-cache-dir -r requirements.txt

# ─── Pre-download EasyOCR model weights during IMAGE BUILD ────────────────────
# This bakes the model weights (~400MB) into the image layer so the container
# starts fast without downloading at runtime. The weights go to /root/.EasyOCR/
# which is the default EasyOCR cache directory.
#
# NOTE: This increases the Docker image size but removes the cold-start
# model-download delay. On Render free tier this may OOM during runtime anyway
# (PyTorch CPU inference needs ~1.5GB RAM). If runtime OOM occurs, upgrade plan.
RUN python -c "\
import easyocr; \
print('[Docker build] Downloading EasyOCR English model weights...'); \
easyocr.Reader(['en'], gpu=False, download_enabled=True); \
print('[Docker build] EasyOCR weights cached.')" || \
echo "[Docker build] WARNING: EasyOCR model download failed — will retry at runtime."

# ─── Copy application code ────────────────────────────────────────────────────
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# ─── Runtime ──────────────────────────────────────────────────────────────────
# PORT is injected by Render at runtime
ENV PORT=10000
EXPOSE $PORT

# Health check — Render calls /health after startup
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/health')" || exit 1

CMD uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
