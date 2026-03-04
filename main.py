from dotenv import load_dotenv
load_dotenv()  # Вызываем загрузку переменных ДО всех остальных импортов

import asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from APP.Database.models import async_main_db
from APP.Game.requests import close_rooms
from APP.BaseFunc.requests import update_bonus
from config import dp, token
from APP.BaseFunc.keyboards import bot_commands

from APP.BaseFunc.updates import router as updates_router
from APP.BaseFunc.handlers import router as base_handlers_router
from APP.Game.handlers import router as game_handlers_router
from APP.BaseFunc.settings_handlers import router as settings_router
from APP.Game.cards import router as cards_router
from APP.Ads.set_ads import router as ads_router
from APP.Middlewares.errors import router as errors_router
from APP.Game.ai_ending import router as ai_router


async def main():
    # Инициализируем бота с оптимальными дефолтными настройками aiogram
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 1. Запуск базы данных
    await async_main_db()

    await close_rooms()
    
    # 2. Настройка планировщика
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    scheduler.add_job(update_bonus, 'cron', hour=0, minute=0)
    scheduler.start()
    
    # 3. Подключение роутеров
    dp.include_routers(
        updates_router, 
        game_handlers_router, 
        settings_router, 
        cards_router, 
        ads_router, 
        errors_router,
        ai_router
    )
    dp.include_router(base_handlers_router)
    
    # 4. Установка меню команд
    await bot_commands(bot=bot)
    
    # 5. Сброс накопившихся апдейтов
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("Бот успешно запущен и готов к работе!")
    
    # 6. Запуск поллинга
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")