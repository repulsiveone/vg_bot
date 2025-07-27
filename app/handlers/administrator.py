from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from ..database import UserRepository, BroadcastRepository
from core.logger import logger
from core.db import async_session
from ..services import parse_users_for_admin, parse_pending_brodcasts_for_admin
from core.keyboards import get_roles_keyboard
from core.filters import IsAdminFilter


router = Router()
user_repo = UserRepository()
broadcast_repo = BroadcastRepository()

# Состояния FSM
class RoleStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_role_selection = State()

@router.message(Command("all_users"), IsAdminFilter())
async def get_all_users(message: Message, session):
    """Подсчет всех пользователей по ролям."""
    list_of_users = await parse_users_for_admin(user_repo, session)
    result = ""
    for key, value in list_of_users.items():
        result += f"{key}: {value}\n"
    await message.answer(
        result
    )

@router.message(Command("all_broadcasts"), IsAdminFilter())
async def get_all_broadcasts(message: Message, session):
    """Просмотр запланированных рассылок."""
    list_of_broadcasts = await parse_pending_brodcasts_for_admin(broadcast_repo, session)
    result = ""
    for value in list_of_broadcasts.values():
        result += f"Модератор: {value[0]} | Запланированное время: {value[1]}\n"
    await message.answer(
        result
    )

@router.message(Command("give_role"), IsAdminFilter())
async def give_user_role(message: Message, state: FSMContext):
    await message.answer(
        "Введите ID пользователя, которому хотите изменить роль:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RoleStates.waiting_for_user_id)

@router.message(RoleStates.waiting_for_user_id, F.text.isdigit(), IsAdminFilter())
async def process_user_id(message: Message, state: FSMContext):
    user_id = int(message.text)
    await state.update_data(user_id=user_id)
    
    await message.answer(
        f"Выберите роль для пользователя {user_id}:",
        reply_markup=get_roles_keyboard()
    )
    await state.set_state(RoleStates.waiting_for_role_selection)

@router.callback_query(RoleStates.waiting_for_role_selection, F.data.startswith("role_"))
async def process_role_selection(callback: CallbackQuery, state: FSMContext, session):
    role = callback.data.split("_")[1]
    
    if role == "cancel":
        await callback.message.edit_text("Отмена изменения роли")
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data['user_id']
    
    try:
        await user_repo.update_user_role(user_id, role, session)
        await callback.message.edit_text(
            f"✅ Пользователю {user_id} успешно назначена роль {role}"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при изменении роли: {str(e)}"
        )
    
    await state.clear()

