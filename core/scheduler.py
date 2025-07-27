import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.redis import RedisJobStore
from sqlalchemy import create_engine, select
from dotenv import load_dotenv

from app.database import BroadcastRepository
from app.models import StatusBroadcast, Broadcast, User
from app.services import execute_broadcast
from .db import async_session
from .logger import logger


load_dotenv()

"""Используем синхронный движок БД, для работы с apscheduler"""
DATABASE_URL = os.getenv("DATABASE_URL").replace("+asyncpg", "+psycopg2")

sync_engine = create_engine(DATABASE_URL)
jobstore = SQLAlchemyJobStore(engine=sync_engine)

scheduler = AsyncIOScheduler()
scheduler.add_jobstore(jobstore)

async def init_scheduler(bot):
    scheduler._bot = bot
    if not scheduler.running:
        scheduler.start()

# Функции для работы с задачами

broadcast_repo = BroadcastRepository()

async def save_and_schedule_broadcast(data: dict, scheduled_time: datetime, user_id: int, session):
    """Сохраняет рассылку в БД и планирует задачу."""
    broadcast = await broadcast_repo.save_schedule(
        user_id,
        data,
        scheduled_time,
        StatusBroadcast.PENDING,
        session,
        )
    
    # Планируем задачу
    scheduler.add_job(
        execute_scheduled_broadcast,
        'date',
        run_date=scheduled_time,
        args=[broadcast.id],
        id=f"broadcast_{broadcast.id}"
    )
    return broadcast

async def execute_scheduled_broadcast(broadcast_id: int, session):
    """Выполнение запланированной рассылки."""
    broadcast = await session.get(Broadcast, broadcast_id)
    if not broadcast or broadcast.status != StatusBroadcast.PENDING:
        return
    
    bot = scheduler._bot
    users = await session.execute(select(User))
    users = users.scalars().all()
    
    success, errors, successful_users = await execute_broadcast(
        bot=bot,
        data=broadcast.content,
        users=users
    )
    
    # Обновляем статус
    broadcast.status = StatusBroadcast.SENT
    broadcast.stats = {
        "total": len(users),
        "success": success,
        "errors": errors
    }
    
    await session.commit()