import json
import redis
import time
from typing import Optional, Any
from core.config import get_settings

settings = get_settings()

class InMemoryCache:
    """Fallback cache using python memory"""
    def __init__(self):
        self._store = {}
        print("⚠️ Using In-Memory Cache (Redis unavailable)")

    def get_json(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if entry['expires'] < time.time():
            del self._store[key]
            return None
        return entry['data']

    def set_json(self, key: str, value: Any, ttl_seconds: int = 3600):
        self._store[key] = {
            'data': value,
            'expires': time.time() + ttl_seconds
        }

class CacheService:
    def __init__(self):
        self.backend = None
        
        # Try Redis First
        if settings.REDIS_URL:
            try:
                self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self.redis.ping()
                self.backend = "redis"
                print("✅ Connected to Redis Cache")
            except Exception as e:
                print(f"Redis connect failed: {e}")
        
        # Fallback
        if not self.backend:
            self.memory = InMemoryCache()
            self.backend = "memory"

    def get_json(self, key: str) -> Optional[Any]:
        if self.backend == "redis":
            try:
                data = self.redis.get(key)
                return json.loads(data) if data else None
            except Exception: 
                return None
        else:
            return self.memory.get_json(key)

    def set_json(self, key: str, value: Any, ttl_seconds: int = 3600):
        if self.backend == "redis":
            try:
                self.redis.setex(key, ttl_seconds, json.dumps(value))
            except Exception as e:
                print(f"Cache set failed: {e}")
        else:
            self.memory.set_json(key, value, ttl_seconds)

# Singleton Instance
cache = CacheService()
