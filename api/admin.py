from fastapi import APIRouter, HTTPException, Depends
from core.rate_limit import grant_quota_boost, get_quota_boost, get_redis
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])

async def verify_admin(admin_role: str):
    """Verify caller is an admin"""
    if admin_role.lower() not in ["admin", "administrator"]:
        raise HTTPException(status_code=403, detail="Unauthorized. Admin access required.")
    return True

@router.post("/grant-quota")
async def grant_quota_endpoint(
    admin_role: str,
    target_user_id: str,
    additional_messages: int
):
    """
    Admin endpoint to grant additional message quota to a user.
    
    Example: POST /admin/grant-quota
    {
        "admin_role": "admin",
        "target_user_id": "123",
        "additional_messages": 10
    }
    """
    await verify_admin(admin_role)
    
    if additional_messages < 1 or additional_messages > 100:
        raise HTTPException(status_code=400, detail="Invalid quota amount (1-100)")
    
    result = grant_quota_boost(target_user_id, additional_messages)
    return {
        "status": "granted",
        "user_id": target_user_id,
        "bonus_messages": additional_messages,
        "granted_at": datetime.now().isoformat()
    }

@router.get("/usage-stats")
async def get_usage_stats(admin_role: str):
    """
    Admin endpoint to view rate limit usage across users.
    Returns users who hit their rate limit today.
    """
    await verify_admin(admin_role)
    
    r = get_redis()
    today = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "date": today,
        "users_at_limit": [],
        "total_users_tracked": 0
    }
    
    if r:
        # Scan for rate limit keys
        pattern = f"rate_limit:*:{today}"
        keys = r.keys(pattern)
        
        for key in keys:
            user_id = key.split(":")[1]
            count = int(r.get(key) or 0)
            bonus = int(r.get(f"quota_boost:{user_id}") or 0)
            
            # Get default limit from settings
            from core.config import get_settings
            settings = get_settings()
            total_limit = settings.RATE_LIMIT_PER_DAY + bonus
            
            if count >= total_limit:
                stats["users_at_limit"].append({
                    "user_id": user_id,
                    "messages_used": count,
                    "limit": total_limit,
                    "bonus": bonus
                })
            
        stats["total_users_tracked"] = len(keys)
    
    return stats
