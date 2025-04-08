from fastapi import (
    APIRouter,
)

from app.admin.access import CurrentAdminUser
from app.admin.schemas import UserResponse

router = APIRouter()


@router.get("/self")
async def user_self(current_user: CurrentAdminUser) -> UserResponse:
    return UserResponse.from_orm(current_user)
