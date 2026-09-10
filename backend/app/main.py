from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.routers import scans, reports, officer, dashboard, auth, products

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
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Register Routers
app.include_router(scans.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(officer.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)

# Serve uploaded images statically
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "NEEDS_REVIEW",
            "public_label": "More evidence or human review required",
            "error_detail": str(exc),
            "disclaimer": "This platform performs image-based Legal Metrology compliance screening. Exceptions default safely to NEEDS_REVIEW."
        }
    )
