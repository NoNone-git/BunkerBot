from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
import os
from aiogram import Dispatcher
from dotenv import load_dotenv

load_dotenv()

admin_id = int(os.getenv('ADMIN_ID', 0))
error_chat_id = int(os.getenv('ERROR_CHAT_ID', 0))
log_chat_id = int(os.getenv('LOG_CHAT_ID', 0))
invite_chat_id = int(os.getenv('INVITE_CHAT_ID', 0))
token = os.getenv('TOKEN')
bot_username = os.getenv('BOT_USERNAME')
db_url = os.getenv('SQLITE_URL')
query = os.getenv('QUERY_COMMAND')
query_split = os.getenv('QUERY_SPLIT')

# Получаем bot_id прямо из токена без инициализации самого бота
# Это решает проблему RuntimeError: no running event loop
bot_id = int(token.split(':')[0]) if token else 0
storage = MemoryStorage()

dp = Dispatcher(storage=storage)

rooms: dict = {}

async def user_state(user_id, bot_id):
    return FSMContext(
        key=StorageKey(
            chat_id=user_id,
            user_id=user_id,
            bot_id=bot_id),
        storage=dp.storage)