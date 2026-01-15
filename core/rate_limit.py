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

async def check_rate_limit(user_id: str, user_role: str = "farmer"):
    """
    Enforces a daily rate limit per user.
    - Admins are exempt (unlimited access)
    - Supports quota boosts granted by admins
    - Fallback: Uses In-Memory dict if Redis is missing.
    """
    # ADMIN EXEMPTION
    if user_role.lower() in ["admin", "administrator"]:
        return {
            "limit": "unlimited",
            "remaining": "unlimited",
            "exempt": True,
            "store": "admin"
        }
    
    r = get_redis()
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"rate_limit:{user_id}:{today}"
    bonus_key = f"quota_boost:{user_id}"
    current_count = 0
    bonus_messages = 0

    if r:
        # REDIS PATH
        current_count = r.incr(key)
        if current_count == 1:
            r.expire(key, 86400)
        
        # Check for bonus quota
        bonus_messages = int(r.get(bonus_key) or 0)
    else:
        # MEMORY PATH
        global _memory_limit_store
        if user_id not in _memory_limit_store:
            _memory_limit_store[user_id] = {}
        
        # Reset if new day
        if _memory_limit_store[user_id].get("date") != today:
            _memory_limit_store[user_id] = {"date": today, "count": 0, "bonus": 0}
            
        _memory_limit_store[user_id]["count"] += 1
        current_count = _memory_limit_store[user_id]["count"]
        bonus_messages = _memory_limit_store[user_id].get("bonus", 0)
    
    total_limit = settings.RATE_LIMIT_PER_DAY + bonus_messages
    
    if current_count > total_limit:
        raise HTTPException(
            status_code=429, 
            detail=f"Daily limit reached. You have used your {total_limit} messages for today.",
            headers={"X-RateLimit-Limit": str(total_limit), "X-RateLimit-Remaining": "0"}
        )
    
    return {
        "limit": total_limit,
        "remaining": max(0, total_limit - current_count),
        "bonus": bonus_messages,
        "store": "redis" if r else "memory"
    }

def grant_quota_boost(user_id: str, additional_messages: int):
    """Admin grants additional messages to a user"""
    r = get_redis()
    bonus_key = f"quota_boost:{user_id}"
    
    if r:
        r.set(bonus_key, additional_messages, ex=86400 * 30)  # 30 days expiry
    else:
        global _memory_limit_store
        if user_id not in _memory_limit_store:
            _memory_limit_store[user_id] = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0, "bonus": 0}
        _memory_limit_store[user_id]["bonus"] = additional_messages
    
    return {"user_id": user_id, "bonus_granted": additional_messages}

def get_quota_boost(user_id: str) -> int:
    """Returns current bonus quota for a user"""
    r = get_redis()
    bonus_key = f"quota_boost:{user_id}"
    
    if r:
        return int(r.get(bonus_key) or 0)
    else:
        global _memory_limit_store
        if user_id in _memory_limit_store:
            return _memory_limit_store[user_id].get("bonus", 0)
        return 0
