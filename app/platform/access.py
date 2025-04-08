from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, APIKeyHeader
from jose import jwt
from sqlalchemy import select

from app.config import settings
from app.database import DBSession
from app.models import User


http_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

http_credentials_required_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credentials required from cookie or access token",
    headers={"WWW-Authenticate": "Bearer"},
)


def decode_access_token(access_token: str) -> str:
    try:
        payload = jwt.decode(access_token.split()[1], settings.SECRET_KEY)
        return payload.get("sub", "")
    except Exception:
        raise Exception("Error decoding JWT")


async def get_user_by_id(user_id: str, session: DBSession) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise Exception("User not found")
    return user


async def get_current_user(session: DBSession, access_token: str):
    if access_token:
        try:
            sub = decode_access_token(access_token)
            return await get_user_by_id(user_id=sub, session=session)
        except Exception:
            raise Exception("Invalid credentials")


async def get_current_http_user(
    session: DBSession,
    access_token_cookie: str | None = Depends(
        APIKeyCookie(name="access_token", auto_error=False)
    ),
    access_token_header: str | None = Depends(
        APIKeyHeader(name="Access-Token", auto_error=False)
    ),
):
    access_token = ""
    if access_token_cookie:
        access_token = access_token_cookie
    if access_token_header:
        access_token = access_token_header

    if not access_token:
        raise http_credentials_required_exception

    try:
        return await get_current_user(session=session, access_token=access_token)
    except Exception:
        raise http_credentials_exception


CurrentUser = Annotated[User, Depends(get_current_http_user)]
