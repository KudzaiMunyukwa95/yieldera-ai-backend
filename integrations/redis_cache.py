import json
import redis
from typing import Optional, Any
from core.config import get_settings

settings = get_settings()

class CacheService:
    def __init__(self):
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.is_connected = True
        except Exception as e:
            print(f"Redis Cache unavailable: {e}")
            self.redis = None
            self.is_connected = False

    def get_json(self, key: str) -> Optional[Any]:
        if not self.is_connected: 
            return None
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int = 3600):
        if not self.is_connected:
            return
        try:
            self.redis.setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            print(f"Cache set failed: {e}")

# Singleton Instance
cache = CacheService()
