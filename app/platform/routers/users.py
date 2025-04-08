from fastapi import (
    APIRouter,
)

from app.platform.access import CurrentUser
from app.platform.schemas import UserResponse

router = APIRouter()


@router.get("/self")
async def user_self(current_user: CurrentUser) -> UserResponse:
    return UserResponse.from_orm(current_user)
