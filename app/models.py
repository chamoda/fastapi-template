from __future__ import annotations


from datetime import datetime

import uuid
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import (
    types,
    DateTime,
    String,
    Boolean,
)
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        types.Uuid, primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(60), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
