import traceback
import logging
from aiogram import Router, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types.error_event import ErrorEvent
from config import error_chat_id

router = Router()
last_error: str = ''

@router.error()
async def aiogram_error(event: ErrorEvent, bot: Bot):
    global last_error
    
    current_error_str = str(event.exception)
    if current_error_str == last_error:
        return
    else:
        last_error = current_error_str

    # Безопасное извлечение chat_id и username, чтобы бот не падал на CallbackQuery
    chat_id = "Неизвестно"
    username = "Неизвестно"
    
    if event.update.message is not None:
        chat_id = event.update.message.chat.id
        username = event.update.message.from_user.username or event.update.message.from_user.id
    elif event.update.callback_query is not None:
        if event.update.callback_query.message is not None:
            chat_id = event.update.callback_query.message.chat.id
        username = event.update.callback_query.from_user.username or event.update.callback_query.from_user.id

    text = (f"🛑Ошибка🛑\n \n"
            f"Error: {event.exception}\n"
            f"Chat_id: {chat_id}\n"
            f"Username: @{username}\n \n"
            f"{traceback.format_exc()}")

    try:
        if len(text) > 4096:
            for x in range(0, len(text), 4000):
                await bot.send_message(chat_id=error_chat_id, text=text[x:x+4000])
        else:
            await bot.send_message(chat_id=error_chat_id, text=text)
            
    except TelegramAPIError as _ex:
        # Если бот не может отправить лог (например, его кикнули из чата логов), пишем в консоль
        logging.error(f"Не удалось отправить лог ошибки в Telegram: {_ex}")
        logging.error(f"Исходная ошибка бота: {text}")