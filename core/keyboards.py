from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Reply клавиатуры

def get_admin_keyboard():
    """Клавиатура действий для админов."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="/all_users"),
        KeyboardButton(text="/all_broadcasts")
    )
    builder.row(
        KeyboardButton(text="/give_role"),
    )
    return builder.as_markup(resize_keyboard=True)

def get_moderator_keyboard():
    """Клавиатура для модераторов."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="/broadcast"),
    )
    return builder.as_markup(resize_keyboard=True)

# Inline клавиатуры

def get_roles_keyboard():
    """Клавиатура для выбора ролей."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="User", callback_data="role_user"),
        InlineKeyboardButton(text="Moderator", callback_data="role_moderator"),
        InlineKeyboardButton(text="Admin", callback_data="role_admin"),
        InlineKeyboardButton(text="Cancel", callback_data="role_cancel")
    )
    builder.adjust(2, 1)
    return builder.as_markup()

def get_confirmation_kb():
    """Клавиатура подтверждения рассылки."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="broadcast_confirm")
    builder.button(text="🕐 Запланировать отправку", callback_data="broadcast_schedule")
    builder.button(text="✏️ Редактировать", callback_data="broadcast_edit")
    builder.button(text="❌ Отменить", callback_data="broadcast_cancel")
    builder.adjust(2, 2)
    return builder.as_markup()

def get_schedule_keyboard():
    """Клавиатура для планировки времени для рассылок."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Через 1 час", callback_data="schedule_1h"),
        InlineKeyboardButton(text="Через 3 часа", callback_data="schedule_3h"),
        InlineKeyboardButton(text="Завтра", callback_data="schedule_tomorrow"),
        InlineKeyboardButton(text="Указать время", callback_data="schedule_custom"),
        InlineKeyboardButton(text="Отмена", callback_data="schedule_cancel"),
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()