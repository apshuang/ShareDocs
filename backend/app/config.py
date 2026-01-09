from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "ShareDocs"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql://sharedocs_user:sharedocs@localhost:5432/sharedocs"
    SECRET_KEY: str = "5ed52db85b9348b491a3aa4cd2f5a006f02e419eea4ccb843e3c3e323a656f3e"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60*24
    DOCUMENTS_DIR: str = "/home/ubuntu/ShareDocs/backend/data/documents"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

