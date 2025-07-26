from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..database import UserRepository
from ..models import UserRole
from core.db import async_session
from core.keyboards import get_admin_keyboard, get_moderator_keyboard


router = Router()
user = UserRepository()

@router.message(Command("start"))
async def cmd_start_user(message: Message):
    """Обработка начальной команды."""
    async with async_session() as session:
        curr_user = await user.create_user_or_return(
            user_id=message.from_user.id,
            username=message.from_user.username,
            session=session
            )
        if curr_user.role == UserRole.ADMIN:
            await message.answer(
                "Панель администратора",
                reply_markup=get_admin_keyboard()
            )
        elif curr_user.role == UserRole.MODERATOR:
            await message.answer(
                "Панель модератора",
                reply_markup=get_moderator_keyboard()
            )
        else:
            await message.answer("Вы подписались на рассылку")