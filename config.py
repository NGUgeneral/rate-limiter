from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Enforce strict validation for the Redis URL string
    redis_url: str = Field(..., validation_alias="REDIS_URL")
    
    # Configurable IP fallbacks with solid baseline defaults
    default_ip_limit: int = Field(100, validation_alias="DEFAULT_IP_LIMIT")
    default_ip_window: int = Field(60, validation_alias="DEFAULT_IP_WINDOW")
    
    # Automatically scan for a local .env file when debugging locally
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()