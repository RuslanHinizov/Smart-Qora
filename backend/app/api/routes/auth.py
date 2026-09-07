from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import LoginResponse, UserRead
from app.core.config import get_settings
from app.core.security import SESSION_COOKIE, create_access_token, verify_password
from app.db.database import get_session
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(response: Response, form: OAuth2PasswordRequestForm = Depends(),
                session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.username == form.username))
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    token = create_access_token(user.id, user.role.value)
    cfg = get_settings()
    response.set_cookie(
        SESSION_COOKIE, token, max_age=cfg.access_token_ttl_hours * 3600,
        httponly=True, secure=cfg.cookie_secure, samesite="strict", path="/",
    )
    return LoginResponse(access_token=token, token_type="bearer", role=user.role.value)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, _user: User = Depends(get_current_user)):
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=get_settings().cookie_secure, samesite="strict",
    )


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)):
    return user
