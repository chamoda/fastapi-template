import secrets
from jose import jwt
from urllib.parse import urljoin

from fastapi.templating import Jinja2Templates

from app.config import settings

templates = Jinja2Templates(directory="templates")


def generate_jwt_token(data: dict) -> str:
    return jwt.encode(data, settings.SECRET_KEY)


def generate_token(length=32) -> str:
    return secrets.token_hex(length)


def get_obj_url(filename: str) -> str:
    return urljoin(settings.OBJ_URL + "/", filename)
