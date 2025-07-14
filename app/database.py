from typing import Annotated

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
    AsyncSession,
)
from app.config import settings
from sqlalchemy.orm import DeclarativeBase
from fastapi import Depends

async_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.SQLALCHEMY_ECHO,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, expire_on_commit=False
)


class Base(AsyncAttrs, DeclarativeBase):
    """subclasses will be converted to dataclasses"""


async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


DBSession = Annotated[AsyncSession, Depends(get_db)]
