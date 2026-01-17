from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Yieldera AI Backend"
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # External APIs
    GEE_API_TOKEN: str  # Google Earth Engine API token for NDVI backend
    
    # Security
    INTERNAL_API_KEY: str  # Shared secret for the PHP Bridge
    ADMIN_TOKEN: str  # Token for yieldera-alerts-main API
    PHP_BRIDGE_URL: str = "http://localhost/dashboard/api/internal/ai_bridge.php"
    ALLOWED_ORIGINS: list[str] = [
        "https://yieldera.net", 
        "https://www.yieldera.net", 
        "http://localhost:3000"
    ]
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Limits
    RATE_LIMIT_PER_DAY: int = 5

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
