from aiogram.filters import BaseFilter
from aiogram import types
from app.database import UserRepository

from .logger import logger


user = UserRepository()

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        logger.info(f"INFO:  {message.from_user.id}")
        role = await user.get_user_role(message.from_user.id)
        return role == "admin"
    
class IsModeratorFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        role = await user.get_user_role(message.from_user.id)
        return role in ["moderator", "admin"]