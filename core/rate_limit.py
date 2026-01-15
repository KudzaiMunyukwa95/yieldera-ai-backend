import redis
from datetime import datetime
from fastapi import HTTPException
from core.config import get_settings

settings = get_settings()

# Initialize Redis Connection
# In production, use connection pool
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Warning: Redis connection failed. Rate limiting may be disabled. {e}")
    r = None

async def check_rate_limit(user_id: str):
    """
    Enforces a daily rate limit per user.
    New Requirement: 5 messages per day.
    """
    if not r:
        return True # Fail open if Redis is down (or handle strictly)

    today = datetime.now().strftime("%Y-%m-%d")
    key = f"rate_limit:{user_id}:{today}"
    
    # Atomic Increment
    current_count = r.incr(key)
    
    # Set expiry to 24 hours if it's a new key
    if current_count == 1:
        r.expire(key, 86400)
    
    if current_count > settings.RATE_LIMIT_PER_DAY:
        raise HTTPException(
            status_code=429, 
            detail=f"Daily limit reached. You have used your {settings.RATE_LIMIT_PER_DAY} free messages for today."
        )
    
    return {
        "limit": settings.RATE_LIMIT_PER_DAY,
        "remaining": max(0, settings.RATE_LIMIT_PER_DAY - current_count)
    }
