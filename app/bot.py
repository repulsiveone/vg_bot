import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from .handlers import home, moderator, administrator
from core.db import init_db
from core.scheduler import init_scheduler, scheduler
from core.middlewares import setup_middlewares


load_dotenv()

async def on_startup(bot: Bot):
    """Функция инициализации при старте"""
    await init_scheduler(bot)

async def init_scheduler(bot: Bot):
    """Инициализация планировщика с ботом"""
    scheduler._bot = bot
    if not scheduler.running:
        scheduler.start()


# Запуск бота
async def main():
    # 1. Инициализация БД
    await init_db()
    
    # 2. Создает экземпляры бота и диспетчера
    bot = Bot(token=os.environ.get("TG_TOKEN"))
    dp = Dispatcher()

    # 3. Инициализация
    setup_middlewares(dp)
    await on_startup(bot)
    
    # 4. Роутеры
    dp.include_router(home.router)
    dp.include_router(moderator.router)
    dp.include_router(administrator.router)
    
    # 5. Запуск бота
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())