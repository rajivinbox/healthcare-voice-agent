from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    anthropic_api_key: str = ""

    # Voice
    elevenlabs_api_key: str = ""

    # Google Calendar
    google_service_account_file: str = ""
    google_calendar_id: str = ""

    # Excel
    excel_data_path: str = "data/patients.xlsx"

    # App
    app_env: str = "demo"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def use_google_calendar(self) -> bool:
        return bool(self.google_service_account_file and self.google_calendar_id)


settings = Settings()
