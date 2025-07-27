from aiogram import Dispatcher

from ..db import async_session
from .database import DatabaseMiddleware


def setup_middlewares(dp: Dispatcher) -> None:
    dp.update.middleware(DatabaseMiddleware(async_session))