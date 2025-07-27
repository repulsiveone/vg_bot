from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from ..database import UserRepository, BroadcastRepository
from ..services import extract_buttons_from_text, ask_confirmation, safe_edit_message, execute_broadcast
from core.keyboards import get_schedule_keyboard
from core.filters import IsModeratorFilter
from core.scheduler import save_and_schedule_broadcast
from core.logger import logger
from core.db import async_session


router = Router()
user_repo = UserRepository()
broadcast_repo = BroadcastRepository()

# Состояния FSM
class BroadcastStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirmation = State()
    waiting_for_schedule_time = State()
    waiting_for_custom_time = State()

@router.message(Command("broadcast"), IsModeratorFilter())
async def start_broadcast(message: Message, state: FSMContext):
    await message.answer(
        "📢 <b>Создание рассылки</b>\n\n"
        "Отправьте мне сообщение для рассылки. Форматы:\n"
        "- <b>Жирный</b>, <i>курсив</i>, <code>код</code>\n"
        "- Ссылки: [текст](https://example.com)\n"
        "- Кнопки: добавьте в конце сообщения\n\n"
        "Пример:\n"
        "<i>Привет!</i> Это [ссылка](https://example.com)\n"
        "---\n"
        "Кнопка1 | https://site1.com\n"
        "Кнопка2 | callback:action1",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_content)

@router.message(BroadcastStates.waiting_for_content, F.content_type == "text")
async def process_text_broadcast(message: Message, state: FSMContext):
    """Принимает текстовое сообщение, извлекает кнопки и сохраняет данные для рассылки."""
    parts = message.text.split('\n---\n')
    text_part = parts[0]
    
    buttons_in_text, clean_text = extract_buttons_from_text(text_part)
    
    additional_buttons = []
    if len(parts) > 1:
        for line in parts[1].split('\n'):
            if ' | ' in line:
                btn_text, btn_action = line.split(' | ', 1)
                additional_buttons.append((btn_text.strip(), btn_action.strip()))
    
    all_buttons = buttons_in_text + additional_buttons
    
    await state.update_data(
        content_type="text",
        text=clean_text,
        buttons=all_buttons
    )
    await ask_confirmation(message, state)

@router.message(BroadcastStates.waiting_for_content, F.content_type.in_({'photo', 'video', 'animation'}))
async def process_media_broadcast(message: Message, state: FSMContext):
    """Принимает фото/видео/GIF, извлекает подпись и кнопки, сохраняет данные для рассылки."""
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    else:
        file_id = message.animation.file_id
    
    caption = message.caption or ""
    buttons_in_caption, clean_caption = extract_buttons_from_text(caption)
    
    additional_buttons = []
    if '---' in caption:
        caption_parts = caption.split('---')
        clean_caption = caption_parts[0]
        if len(caption_parts) > 1:
            for line in caption_parts[1].split('\n'):
                if ' | ' in line:
                    btn_text, btn_action = line.split(' | ', 1)
                    additional_buttons.append((btn_text.strip(), btn_action.strip()))
    
    all_buttons = buttons_in_caption + additional_buttons
    
    await state.update_data(
        content_type=message.content_type,
        file_id=file_id,
        caption=clean_caption,
        buttons=all_buttons
    )
    await ask_confirmation(message, state)

@router.callback_query(BroadcastStates.waiting_for_confirmation, F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot, session):
    data = await state.get_data()
    users = await user_repo.get_users(session)
    logger.info(f"INFO: {data, data['content_type']}")

    await execute_broadcast(bot, data, users, callback)
    await state.clear()

@router.callback_query(BroadcastStates.waiting_for_confirmation, F.data == "broadcast_schedule")
async def show_schedule_options(callback: CallbackQuery, state: FSMContext):
    """Показывает клавиатуру выбора времени."""
    await callback.message.answer(
        "⏰ Выберите время отправки рассылки:",
        reply_markup=get_schedule_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_schedule_time)
    await callback.answer()

@router.callback_query(BroadcastStates.waiting_for_schedule_time, F.data.startswith("schedule_"))
async def handle_schedule_selection(callback: CallbackQuery, state: FSMContext, session):
    """Обрабатывает выбор времени."""
    action = callback.data.split("_")[1]
    
    if action == "cancel":
        await callback.message.edit_text("❌ Планирование отменено")
        await state.clear()
        return
    
    data = await state.get_data()
    now = datetime.now()
    
    if action == "1h":
        scheduled_time = now + timedelta(hours=1)
    elif action == "3h":
        scheduled_time = now + timedelta(hours=3)
    elif action == "tomorrow":
        scheduled_time = now + timedelta(days=1)
    elif action == "custom":
        await callback.message.answer("Введите дату и время в формате DD.MM.YYYY HH:MM")
        await state.set_state(BroadcastStates.waiting_for_custom_time)
        return
    
    # Сохраняем и планируем рассылку
    broadcast = await save_and_schedule_broadcast(
        data, 
        scheduled_time, 
        callback.from_user.id,
        session
    )
    
    await callback.message.edit_text(
        f"✅ Рассылка запланирована на {scheduled_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"ID: {broadcast.id}"
    )
    await state.clear()
    await callback.answer()

@router.message(BroadcastStates.waiting_for_custom_time, F.text.regexp(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}'))
async def handle_custom_time(message: Message, state: FSMContext, session):
    """Обрабатывает ручной ввод времени."""
    try:
        scheduled_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        if scheduled_time < datetime.now():
            await message.answer("❌ Указано прошедшее время. Введите будущую дату:")
            return
            
        data = await state.get_data()
        broadcast = await save_and_schedule_broadcast(
            data, 
            scheduled_time, 
            message.from_user.id,
            session,
        )
        
        await message.answer(
            f"✅ Рассылка запланирована на {scheduled_time.strftime('%d.%m.%Y %H:%M')}\n"
            f"ID: {broadcast.id}"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите дату в формате DD.MM.YYYY HH:MM")

@router.callback_query(BroadcastStates.waiting_for_confirmation, F.data == "broadcast_edit")
async def edit_broadcast(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    if data['content_type'] == "text":
        await callback.message.answer(
            "Отправьте исправленный текст сообщения:",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "Отправьте новый медиа-файл с исправленной подписью:",
            parse_mode="HTML"
        )
    
    await state.set_state(BroadcastStates.waiting_for_content)
    await callback.answer()

@router.callback_query(BroadcastStates.waiting_for_confirmation, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await safe_edit_message(message=callback, text="❌ Рассылка отменена")
    
    await state.clear()
    await callback.answer()