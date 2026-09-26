from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        uid, role = payload.get("sub"), payload.get("role")
        if not uid or role not in {"doctor", "pathologist"}:
            raise ValueError()
    except (JWTError, ValueError):
        raise HTTPException(401, "Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, uid)
    if not user or user.role != role:
        raise HTTPException(401, "Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


def current_doctor(user: User = Depends(current_user)) -> User:
    if user.role != "doctor":
        raise HTTPException(403, "Doctor account required")
    return user


def current_pathologist(user: User = Depends(current_user)) -> User:
    if user.role != "pathologist":
        raise HTTPException(403, "Pathologist account required")
    if not user.assigned_doctor_id:
        raise HTTPException(403, "Pathologist must be assigned to a doctor")
    return user
