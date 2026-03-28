from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, get_password_hash, verify_password
from database import get_db
from models import User
from schemas import UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def resp(success: bool, data, message: str):
    return {"success": success, "data": data, "message": message}


def validate_bcrypt_password_length(password: str) -> None:
    # bcrypt only supports up to 72 bytes of input.
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password is too long for bcrypt (max 72 UTF-8 bytes).",
        )


@router.post("/register")
async def register(payload: UserCreate, db: Session = Depends(get_db)):
    validate_bcrypt_password_length(payload.password)
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return resp(True, {"token": token, "user": UserOut.model_validate(user).model_dump()}, "Registration successful")


@router.post("/login")
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    validate_bcrypt_password_length(payload.password)
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return resp(True, {"token": token, "user": UserOut.model_validate(user).model_dump()}, "Login successful")


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return resp(True, UserOut.model_validate(current_user).model_dump(), "User fetched")
