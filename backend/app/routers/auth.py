from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.models import User
from backend.app.schemas.schemas import UserLogin, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    # Simple role determination for demonstration credentials
    if payload.email.startswith("officer"):
        role = "OFFICER"
        full_name = "Inspector R. K. Sharma"
    elif payload.email.startswith("admin"):
        role = "ADMIN"
        full_name = "System Administrator"
    else:
        role = "CITIZEN"
        full_name = "Citizen User"

    return TokenResponse(
        access_token=f"mock_jwt_token_{role.lower()}_2026",
        token_type="bearer",
        role=role,
        full_name=full_name
    )

@router.get("/me")
def get_current_user():
    return {
        "email": "officer@legalmetrology.gov.in",
        "full_name": "Inspector R. K. Sharma",
        "role": "OFFICER",
        "badge_number": "LM-OFFICER-1082"
    }
