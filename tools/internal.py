import requests
from core.config import get_settings
from core.audit import AuditLog

settings = get_settings()

def get_fields_via_bridge(user_context: dict) -> list:
    """
    Fetches the user's fields by calling the PHP Logic via the Bridge.
    """
    url = settings.PHP_BRIDGE_URL
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "action": "get_fields",
        "auth_key": settings.INTERNAL_API_KEY,  # Moved to Body for reliability
        "user_id": user_context.get("user_id"),
        "role": user_context.get("role"),
        "entity_id": user_context.get("entity_id")
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # PHP api returns { type: FeatureCollection, features: [...] }
        # We simplify this for the AI to save tokens
        features = data.get("features", [])
        
        simplified_fields = []
        for f in features:
            props = f.get("properties", {})
            simplified_fields.append({
                "id": props.get("id"),
                "name": props.get("name"),
                "crop": props.get("crop"),
                "area_ha": props.get("area_ha"),
                "location": f.get("geometry", {}).get("coordinates") # [lon, lat]
            })
            
        AuditLog.log_event(user_context.get("user_id"), "TOOL_EXECUTION", {"tool": "get_fields", "count": len(simplified_fields)})
        return simplified_fields

    except Exception as e:
        AuditLog.log_event(user_context.get("user_id"), "TOOL_ERROR", {"tool": "get_fields", "error": str(e)})
        return {"error": "Could not fetch fields", "details": str(e)}
