import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import create_engine
from dotenv import load_dotenv

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