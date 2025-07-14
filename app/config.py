from typing import Optional
from pydantic import EmailStr, SecretStr, field_validator
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

    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: SecretStr = SecretStr("")
    MAIL_PORT: int = 25
    MAIL_SERVER: str = "localhost"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = False
    MAIL_FROM: EmailStr = "test@example.com"
    MAIL_FROM_NAME: Optional[str] = None
    MAIL_USE_CREDENTIALS: bool = True
    MAIL_VALIDATE_CERTS: bool = True

    CORS_ORIGINS: str = "http://localhost:3000"

    # JWT Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_ALGORITHM: str = "HS256"

    # Redis settings for rate limiting
    REDIS_URL: str = "redis://localhost:6379/0"

    # Platform URL for email links
    PLATFORM_URL: str = "http://localhost:3000"

    # Cloudflare API token for SSL certificates
    CLOUDFLARE_API_TOKEN: Optional[str] = None

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        if not v or not v.strip():
            raise ValueError(
                "SECRET_KEY cannot be empty. Set SECRET_KEY environment variable."
            )
        return v

    @field_validator("SQLALCHEMY_DATABASE_URI")
    @classmethod
    def validate_database_uri(cls, v):
        if not v or not v.strip():
            raise ValueError(
                "SQLALCHEMY_DATABASE_URI cannot be empty. Set SQLALCHEMY_DATABASE_URI environment variable."
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
