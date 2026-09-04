from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import LoginResponse, UserRead
from app.core.security import create_access_token, verify_password
from app.db.database import get_session
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.username == form.username))
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    return LoginResponse(
        access_token=create_access_token(user.id, user.role.value), token_type="bearer", role=user.role.value
    )


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    return user
