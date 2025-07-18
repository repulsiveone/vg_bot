from sqlalchemy import select, update
from functools import wraps

from .models import User, UserRole, Broadcast
from core.db import async_session
from core.logger import logger


def with_session(func):
    """Декоратор для управления сессией"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with async_session() as session:
            kwargs['session'] = session
            return await func(self, *args, **kwargs)
    return wrapper

class UserRepository:
    @with_session
    async def create_user_or_return(self, user_id: int, username: str, *, session) -> User:
        result = await session.execute(select(User).where(User.id == user_id))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            return existing_user
            
        user = User(id=user_id, username=username)
        session.add(user)
        await session.commit()
        return user

    @with_session
    async def get_users(self, *, session):
        result = await session.execute(select(User))
        return result.scalars().all()

    @with_session
    async def get_user_role(self, user_id: int, *, session) -> str:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return UserRole.USER.value if user is None else user.role.value

    @with_session
    async def update_user_role(self, user_id: int, role: str, *, session):
        try:
            role_enum = UserRole(role.lower())
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(role=role_enum)
            )
            await session.commit()
        except ValueError as e:
            raise ValueError(f"Invalid role: {role}") from e

class BroadcastRepository:
    @with_session
    async def save_schedule(self, user_id: int, data, scheduled_time, status, *, session):
        broadcast = Broadcast(
            created_by=user_id,
            content=data,
            scheduled_time=scheduled_time,
            status=status
        )
        session.add(broadcast)
        await session.commit()

        return broadcast
    
    @with_session
    async def get_broadcasts(self, *, session):
        result = await session.execute(select(Broadcast))
        return result.scalars().all()
    
    @with_session
    async def get_pending_broadcasts(self, *, session):
        result = await session.execute(
            select(Broadcast)
            .where(Broadcast.status=="PENDING")
        )
        return result.scalars().all()