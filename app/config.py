import os
from pydantic_settings import BaseSettings  # Changed import

class Settings(BaseSettings):
    app_name: str = "Survey Grade Coordinate Converter"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security
    allowed_origins: list = ["*"]  # In production, specify your domain
    
    class Config:
        env_file = ".env"

settings = Settings()