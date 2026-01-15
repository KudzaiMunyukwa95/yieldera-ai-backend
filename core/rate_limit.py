import redis
from datetime import datetime
from fastapi import HTTPException
from core.config import get_settings

settings = get_settings()

# In-Memory Backup
_memory_limit_store = {}

def get_redis():
    try:
        if settings.REDIS_URL:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.ping()
            return r
    except Exception:
        pass
    return None

async def check_rate_limit(user_id: str):
    """
    Enforces a daily rate limit per user.
    Fallback: Uses In-Memory dict if Redis is missing.
    """
    r = get_redis()
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"rate_limit:{user_id}:{today}"
    current_count = 0

    if r:
        # REDIS PATH
        current_count = r.incr(key)
        if current_count == 1:
            r.expire(key, 86400)
    else:
        # MEMORY PATH
        # Clean old keys from other days (simple GC)
        global _memory_limit_store
        if user_id not in _memory_limit_store:
            _memory_limit_store[user_id] = {}
        
        # Reset if new day
        if _memory_limit_store[user_id].get("date") != today:
            _memory_limit_store[user_id] = {"date": today, "count": 0}
            
        _memory_limit_store[user_id]["count"] += 1
        current_count = _memory_limit_store[user_id]["count"]
    
    if current_count > settings.RATE_LIMIT_PER_DAY:
        raise HTTPException(
            status_code=429, 
            detail=f"Daily limit reached. You have used your {settings.RATE_LIMIT_PER_DAY} free messages for today."
        )
    
    return {
        "limit": settings.RATE_LIMIT_PER_DAY,
        "remaining": max(0, settings.RATE_LIMIT_PER_DAY - current_count),
        "store": "redis" if r else "memory"
    }
