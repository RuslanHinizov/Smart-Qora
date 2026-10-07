from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.schemas import UserCreate, UserRead, UserUpdate
from app.core.security import hash_password
from app.db.database import get_session
from app.db.models import Role, User

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserRead])
async def list_users(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(User).order_by(User.id))).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "A user with this username already exists") from None
    await session.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, payload: UserUpdate, session: AsyncSession = Depends(get_session)):
    """Users are deactivated rather than deleted: inventory movements keep
    pointing at whoever recorded them."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    await session.flush()
    admins = await session.scalar(
        select(func.count()).select_from(User).where(User.role == Role.admin, User.is_active.is_(True)))
    if not admins:
        await session.rollback()
        raise HTTPException(409, "At least one active admin is required")
    await session.commit()
    await session.refresh(user)
    return user
