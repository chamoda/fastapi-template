from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    PROJECT_NAME: str = "app"
    LOG_LEVEL: str = "DEBUG"
    SECRET_KEY: str = ""
    SQLALCHEMY_DATABASE_URI: str = ""
    SQLALCHEMY_ECHO: bool = False
    SECURE_COOKIE: bool = True
    SLOWDOWN_DELAY: int = 0
    OBJ_URL: str = ""


settings = Settings()
