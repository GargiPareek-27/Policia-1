from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.account import AccountRead
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=AccountRead, status_code=201)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    role = data.role
    if role not in {"doctor", "pathologist"}:
        raise HTTPException(422, "role must be doctor or pathologist")
    if role == "doctor" and data.doctor_id:
        raise HTTPException(422, "doctor_id may only be supplied for a pathologist")
    if role == "pathologist" and not data.doctor_id:
        raise HTTPException(422, "doctor_id is required for a pathologist")
    email = data.email.lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Email already registered")
    doctor = None
    if role == "pathologist":
        doctor = db.query(User).filter_by(id=data.doctor_id, role="doctor").first()
        if not doctor:
            raise HTTPException(404, "Doctor not found")
        if doctor.pathologist:
            raise HTTPException(409, "Doctor already has an assigned pathologist")
    user = User(name=data.name, email=email, hashed_password=hash_password(data.password), role=role,
                assigned_doctor=doctor if role == "pathologist" else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer"}


@router.get("/me", response_model=AccountRead)
def me(user: User = Depends(current_user)):
    return user
