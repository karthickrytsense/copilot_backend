from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Optional

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GOOGLE_SHEET_ID: Optional[str] = None
    GOOGLE_SHEET_NAME: Optional[str] = "Sheet1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
