from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_menu() -> InlineKeyboardMarkup:
    """Главная клавиатура админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить данные", callback_data="admin_refresh")],
        [InlineKeyboardButton(text="📁 Выгрузить все ID", callback_data="admin_export_ids")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])

def admin_close_kb() -> InlineKeyboardMarkup:
    """Простая клавиатура для закрытия админских сообщений (например, отчетов по рекламе)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ])