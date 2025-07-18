from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, DateTime, BigInteger
from sqlalchemy.types import Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import ENUM as SqlEnum
from enum import Enum
from typing import Optional

from core.db import Base


class UserRole(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class User(Base):
    """Хранение пользователей и ролей."""
    __tablename__ = "user_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(30))
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.USER
    )

class StatusBroadcast(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

class Broadcast(Base):
    """Данные рассылки и планирование."""
    __tablename__ = "broadcast"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("user_info.id"))
    content: Mapped[dict] = mapped_column(JSON)
    scheduled_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[StatusBroadcast] = mapped_column(
        SqlEnum(StatusBroadcast, name="status_broadcast"),
        nullable=False,
        default=StatusBroadcast.PENDING
    )
    stats: Mapped[dict] = mapped_column(JSON, nullable=True)