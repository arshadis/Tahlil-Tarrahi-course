from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if not payload.username.strip() or not payload.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نام کاربری و رمز عبور الزامی است."
        )

    user = authenticate_user(db, payload.username.strip(), payload.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است."
        )

    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
    })

    return LoginResponse(
        access_token=token,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )
