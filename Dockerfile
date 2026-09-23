# ─────────────────────────────────────────────────────────────────────────────
# LM-Screen Production Dockerfile
# Base: python:3.11-slim  (Debian Bookworm, glibc 2.36)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# ─── System libraries ─────────────────────────────────────────────────────────
# Required by Python packages (cannot be installed via pip):
#   libzbar0      — pyzbar barcode engine
#   libgl1        — OpenCV (libGL.so.1)
#   libglib2.0-0  — OpenCV (libgthread-2.0.so, libglib-2.0.so)
#   libgomp1      — PyTorch CPU OpenMP threading
#   libsm6        — OpenCV (libSM.so.6) on some Debian variants
#   libxext6      — OpenCV (libXext.so.6)
#   libxrender1   — OpenCV (libXrender.so.1)
#   wget          — used for health-check smoke test
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── Python dependencies ──────────────────────────────────────────────────────
# Copy requirements first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir \
    && pip install --no-cache-dir -r requirements.txt

# ─── Pre-download EasyOCR model weights (FILE DOWNLOAD ONLY) ──────────────────
#
# IMPORTANT: We do NOT call easyocr.Reader() here.
# easyocr.Reader() initializes PyTorch + CRAFT + recognition models into memory
# and consumes ~500MB RAM — unacceptable during a Docker build step.
#
# Instead we use download_ocr_models.py which:
#   - Uses only Python stdlib (urllib, zipfile) — no torch, no easyocr import
#   - Downloads craft_mlt_25k.pth (~79MB) and english_g2.pth (~14MB)
#   - Writes them to /root/.EasyOCR/model/ (EasyOCR's default cache path)
#   - Uses <50MB RAM total
#
# At container startup, ai/ocr_engine.py loads the pre-cached .pth files.
# No network access is needed at runtime.
#
# If download fails during build (network issue), we allow the build to continue.
# EasyOCR will re-attempt download at runtime via download_enabled=True.
COPY download_ocr_models.py .
RUN python download_ocr_models.py

# ─── Application code ─────────────────────────────────────────────────────────
COPY . .

# Ensure uploads directory exists
RUN mkdir -p uploads

# ─── Runtime environment ──────────────────────────────────────────────────────
# PORT is injected by Render at runtime. Default to 10000 for local docker run.
ENV PORT=10000
EXPOSE $PORT

# ─── Start command ────────────────────────────────────────────────────────────
# Uses the PORT env var injected by Render (never hardcoded to 8000).
# The HTTP server starts immediately; OCR initializes in a background thread.
# /health returns ocr_ready=false while EasyOCR loads, then ocr_ready=true.
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
