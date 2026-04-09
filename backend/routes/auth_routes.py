from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from auth import login_user, register_user, hash_password

router = APIRouter(prefix="/api", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None
    username: str | None = None
    user_id: int | None = None


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = login_user(db, req.username, req.password)
    if user:
        return AuthResponse(
            success=True,
            message="Login successful",
            token=hash_password(req.password),
            username=user.username,
            user_id=user.id,
        )
    return AuthResponse(success=False, message="Invalid credentials")


@router.post("/register", response_model=AuthResponse)
def register(req: LoginRequest, db: Session = Depends(get_db)):
    ok, msg = register_user(db, req.username, req.password)
    return AuthResponse(success=ok, message=msg)
