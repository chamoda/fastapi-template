from fastapi import APIRouter, Response, HTTPException, status
from jose import jwt
from sqlalchemy import select

from app.admin.schemas import AuthRequest, AuthResponse
from app.secuirty import verify_password
from app.models import User
from app.database import DBSession
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health(_: DBSession) -> str:
    return "OK"


@router.post("/auth")
async def auth(
    auth_request: AuthRequest, session: DBSession, response: Response
) -> AuthResponse:
    result = await session.execute(
        select(User).where(
            User.email == auth_request.email.lower(),
            User.is_admin.is_(True),
        )
    )
    user = result.scalars().first()

    if user:
        if verify_password(auth_request.password, user.password):
            access_token = jwt.encode({"sub": str(user.id)}, settings.SECRET_KEY)
            response.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                samesite="lax",
                secure=settings.SECURE_COOKIE,
                httponly=True,
                max_age=2147483647,
            )
            return AuthResponse(access_token=access_token)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/logout")
async def logout(response: Response) -> str:
    response.delete_cookie("access_token")
    return "OK"
