import time
import re
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from collections import defaultdict

from core.logger import logger
from core.keyboards import get_confirmation_kb

# Состояния FSM
class BroadcastStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirmation = State()

# Функции обработки данных
def extract_buttons_from_text(text: str):
    """Извлекает кнопки из текста в формате [Текст](URL)."""
    buttons = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', text)
    clean_text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', '', text)
    return buttons, clean_text.strip()

def build_inline_kb(buttons_data):
    """Создает inline-клавиатуру из списка кнопок."""
    builder = InlineKeyboardBuilder()
    if buttons_data and isinstance(buttons_data, list):
        for btn in buttons_data:
            if len(btn) == 2:
                text, url = btn
                if url.startswith(('http://', 'https://')):
                    builder.button(text=text, url=url)
                else:
                    builder.button(text=text, callback_data=url)
    return builder.as_markup()

async def safe_edit_message(message: CallbackQuery, text: str):
    """Обработка кнопок ответа после предпросмотра рассылки."""
    try:
        await message.message.edit_text(text)
    except:
        try:
            await message.message.edit_caption(caption=text)
        except:
            await message.answer(text, show_alert=True)

# Функции для работы с расслыками

async def send_media_with_caption(bot: Bot, chat_id: int, data: dict):
    """Отправка медиа с подписью и кнопками."""
    caption = data.get('caption', '')
    buttons = data.get('buttons', [])
    
    try:
        if data['content_type'] == "photo":
            await bot.send_photo(
                chat_id=chat_id,
                photo=data['file_id'],
                caption=caption,
                reply_markup=build_inline_kb(buttons),
                parse_mode="HTML"
            )
        elif data['content_type'] == "video":
            await bot.send_video(
                chat_id=chat_id,
                video=data['file_id'],
                caption=caption,
                reply_markup=build_inline_kb(buttons),
                parse_mode="HTML"
            )
        elif data['content_type'] == "animation":
            await bot.send_animation(
                chat_id=chat_id,
                animation=data['file_id'],
                caption=caption,
                reply_markup=build_inline_kb(buttons),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Error sending media to {chat_id}: {str(e)}")
        raise

async def ask_confirmation(message: Message, state: FSMContext):
    """
        Запрашивает у пользователя подтверждение перед отправкой рассылки.
        Определяет тип контента (text или media) и вызывает соответствующий метод предпросмотра.
    """
    data = await state.get_data()
    
    if data['content_type'] == "text":
        preview_text = data['text'][:500] + ("" if len(data['text']) <= 500 else "...")
        await message.answer(
            f"📋 <b>Предпросмотр рассылки:</b>\n\n{preview_text}\n\n"
            f"🔲 Кнопок: {len(data.get('buttons', []))}\n\n"
            "Подтвердите действие:",
            reply_markup=get_confirmation_kb(),
            parse_mode="HTML"
        )
    else:
        await send_media_preview(message, data)
    
    await state.set_state(BroadcastStates.waiting_for_confirmation)

async def send_media_preview(message: Message, media_data: dict):
    """
        Отправляет предпросмотр медиафайлов (фото, видео, GIF).
        Добавляет к медиа описание и кнопки подтверждения.
    """
    try:
        preview_text = (
            f"\n\n📋 <b>Предпросмотр рассылки</b>\n"
            f"🔲 Кнопок: {len(media_data.get('buttons', []))}\n"
            "Подтвердите действие:"
        )
        
        if media_data['content_type'] == 'photo':
            await message.answer_photo(
                photo=media_data['file_id'],
                caption=f"{media_data.get('caption', '')}{preview_text}",
                reply_markup=get_confirmation_kb(),
                parse_mode="HTML"
            )
        elif media_data['content_type'] == 'video':
            await message.answer_video(
                video=media_data['file_id'],
                caption=f"{media_data.get('caption', '')}{preview_text}",
                reply_markup=get_confirmation_kb(),
                parse_mode="HTML"
            )
        elif media_data['content_type'] == 'animation':
            await message.answer_animation(
                animation=media_data['file_id'],
                caption=f"{media_data.get('caption', '')}{preview_text}",
                reply_markup=get_confirmation_kb(),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        await message.answer(
            "❌ Ошибка при создании предпросмотра. Попробуйте еще раз.",
            parse_mode="HTML"
        )

async def execute_broadcast(bot: Bot, data: dict, users: list, callback: CallbackQuery = None):
    """Общая функция для выполнения рассылки (немедленной или запланированной)."""
    if callback:
        await safe_edit_message(message=callback, text="⏳ Рассылка начата...")
    
    success = 0
    errors = 0
    successful_users = []
    start_time = time.perf_counter()
    for user in users:
        try:
            if data['content_type'] == "text":
                await bot.send_message(
                    chat_id=user.id,
                    text=data['text'],
                    reply_markup=build_inline_kb(data.get('buttons', [])),
                    parse_mode="HTML"
                )
            else:
                await send_media_with_caption(
                    bot=bot,
                    chat_id=user.id,
                    data=data
                )
            successful_users.append(user.id)
            success += 1
        except Exception as e:
            errors += 1
            logger.error(f"Error sending to {user.id}: {str(e)}")
    end_time = time.perf_counter()
    result_text = f"✅ Успешно: {success}\n❌ Ошибок: {errors}\n⏰ Время выполнения: {end_time - start_time} сек."
    
    if callback:
        await safe_edit_message(message=callback, text=result_text)
    
    return success, errors, successful_users

# Функции для админа
async def parse_users_for_admin(user_repo):
    result = defaultdict(int)
    all_users = await user_repo.get_users()
    result['total'] = len(all_users)
    for user in all_users:
        result[user.role.value] += 1
    return result

async def parse_pending_brodcasts_for_admin(broadcast_repo):
    result = {}
    all_pending_broadcasts = await broadcast_repo.get_pending_broadcasts()
    for br in all_pending_broadcasts:
        result[br.id] = [br.created_by, br.scheduled_time]
    return result