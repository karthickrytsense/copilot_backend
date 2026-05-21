from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Optional

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GOOGLE_SHEET_ID: Optional[str] = None
    GOOGLE_SHEET_NAME: Optional[str] = "Sheet1"
    GOOGLE_CREDENTIALS_FILE: Optional[str] = None
    OWNER_EMAIL: Optional[str] = None
    OWNER_CALENDAR_ID: Optional[str] = "primary"
    OWNER_TIMEZONE: Optional[str] = "Asia/Kolkata"
    MEETING_DURATION_MINUTES: Optional[int] = 30
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REFRESH_TOKEN: Optional[str] = None
    GOOGLE_WEB_CLIENT_ID: Optional[str] = None
    GOOGLE_WEB_CLIENT_SECRET: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
