import os

from pydantic_settings import BaseSettings

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")


class Settings(BaseSettings):
    database_url: str

    groq_api_key: str = ""
    tavily_api_key: str = ""
    firebase_credentials_json: str = ""

    class Config:
        # Absolute path, so the .env is found no matter which directory
        # uvicorn was launched from.
        env_file = _ENV_FILE
        extra = "ignore"


settings = Settings()
