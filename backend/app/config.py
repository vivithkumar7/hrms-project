from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HRMS API"
    database_url: str = "sqlite:///./hrms.db"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=30, gt=0)
    refresh_token_minutes: int = Field(default=720, gt=0)
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: Literal["strict", "lax", "none"] = "strict"
    upload_dir: str = "uploads"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=120)
    hrms_admin_email: str = ""
    hrms_admin_password: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("jwt_secret_key")
    @classmethod
    def reject_known_placeholder_secrets(cls, value: str) -> str:
        lowered = value.lower()
        if any(marker in lowered for marker in ("replace-with", "change-me", "your-secret", "example-secret")):
            raise ValueError("JWT_SECRET_KEY must be a unique, randomly generated secret")
        return value

    @model_validator(mode="after")
    def validate_cookie_settings(self):
        if self.refresh_cookie_samesite == "none" and not self.refresh_cookie_secure:
            raise ValueError("REFRESH_COOKIE_SECURE must be true when SameSite=None")
        if any((self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_from_email)):
            if not self.smtp_host or not self.smtp_from_email:
                raise ValueError("SMTP_HOST and SMTP_FROM_EMAIL are required when email settings are configured")
            if bool(self.smtp_username) != bool(self.smtp_password):
                raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")
        return self

settings = Settings()