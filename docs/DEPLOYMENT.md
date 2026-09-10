# LM-Screen Deployment Guide

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- OpenCV & dependencies

### 2. Backend Setup
```bash
# Navigate to project root
pip install -r backend/requirements.txt
python -m backend.app.seed
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Docker Deployment
```bash
docker-compose up --build
```
The application will be accessible at:
- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Docs (Swagger): `http://localhost:8000/docs`
