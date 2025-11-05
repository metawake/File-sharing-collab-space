from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "HarveyAI DataRoom API"
    sqlite_url: str = Field(default="sqlite:///./dataroom.db", alias="SQLITE_URL")
    storage_dir: str = Field(default="./storage", alias="STORAGE_DIR")
    session_secret: str = Field(default="dev-change-me", alias="SESSION_SECRET")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")

    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_CLIENT_SECRET"
    )
    google_redirect_uri: Optional[str] = Field(
        default=None, alias="GOOGLE_REDIRECT_URI"
    )

    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    web_base_url: str = Field(default="http://localhost:3000", alias="WEB_BASE_URL")
    allow_email_param: bool = Field(default=True, alias="ALLOW_EMAIL_PARAM")
    demo_seed: bool = Field(default=False, alias="DEMO_SEED")
    seed_room_name: str = Field(default="Demo Room", alias="SEED_ROOM_NAME")
    public_room_id: Optional[int] = Field(default=None, alias="PUBLIC_ROOM_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[call-arg]
