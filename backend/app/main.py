from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.routers import scans, reports, officer, dashboard, auth, products, analytics, cases

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LM-Screen API",
    description="AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform",
    version="2026.1.1"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    from ai.ocr_engine import _reader_ready, _prewarmed_reader, _prewarm_error
    ocr_ready = _reader_ready.is_set() and _prewarmed_reader is not None
    result = {
        "status": "ok" if ocr_ready else "starting",
        "service": "LM-Screen",
        "ocr_ready": ocr_ready,
    }
    if not ocr_ready and _prewarm_error:
        result["ocr_error"] = _prewarm_error
    return result

# Register Routers
app.include_router(scans.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(officer.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(cases.router, prefix=settings.API_V1_PREFIX)

# Serve uploaded images statically
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    # Only expose internal detail in development; scrub in production
    detail = str(exc) if settings.ENV == "development" else "An internal error occurred. Please try again."
    return JSONResponse(
        status_code=500,
        content={
            "status": "NEEDS_REVIEW",
            "public_label": "More evidence or human review required",
            "error_detail": detail,
            "disclaimer": "This platform performs image-based Legal Metrology compliance screening. Exceptions default safely to NEEDS_REVIEW."
        }
    )
