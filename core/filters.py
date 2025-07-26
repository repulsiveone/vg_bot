from aiogram.filters import BaseFilter
from aiogram import types
from app.database import UserRepository

from .logger import logger
from .db import async_session


user = UserRepository()

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        logger.info(f"INFO:  {message.from_user.id}")
        async with async_session() as session:
            role = await user.get_user_role(message.from_user.id, session)
            return role == "admin"
    
class IsModeratorFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        async with async_session() as session:
            role = await user.get_user_role(message.from_user.id, session)
            return role in ["moderator", "admin"]