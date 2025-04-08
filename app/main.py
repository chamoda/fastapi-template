import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination

from app.config import settings
from app.platform.router import router as platform_router
from app.admin.router import router as admin_router


origins = ["http://localhost:3000"]

app = FastAPI(
    title=settings.PROJECT_NAME,
)

platformAPI = FastAPI(
    contact={"name": "Chamoda Pandithage", "email": "chamoda@xaventra.com"},
    description="Platform api endpoints",
    openapi_tags=[{"name": "platform", "description": "Platform enpoints"}],
)
platformAPI.include_router(platform_router)
platformAPI.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_pagination(platformAPI)
app.mount("/platform", platformAPI, "platform")

adminAPI = FastAPI(
    contact={"name": "Chamoda Pandithage", "email": "chamoda@xaventra.com"},
    description="Admin api endpoints",
    openapi_tags=[{"name": "admin", "description": "Admin enpoints"}],
)
adminAPI.include_router(admin_router)
adminAPI.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_pagination(adminAPI)
app.mount("/admin", adminAPI, "admin")


obj_dir = os.path.join(os.getcwd(), "obj")
if os.path.exists(obj_dir):
    app.mount("/obj", StaticFiles(directory="obj"), name="obj")
