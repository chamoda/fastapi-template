from fastapi.routing import APIRouter
from .routers import users, meta, registrations

router = APIRouter()

router.include_router(meta.router)
router.include_router(registrations.router)
router.include_router(users.router)
