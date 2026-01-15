import requests
from core.config import get_settings

settings = get_settings()

ALERTS_API_URL = "https://yieldera-alerts-main.onrender.com/api"
ADMIN_TOKEN = settings.INTERNAL_API_KEY  # Reuse existing internal API key

def get_alerts_from_system(user_context: dict, status: str = "active") -> list:
    """
    Fetches existing alerts from yieldera-alerts-main backend.
    IMPORTANT: Use this for alert queries, NOT portfolio data.
    
    Args:
        user_context: User context dict
        status: "active" or "all"
    
    Returns:
        List of alerts with field names, types, thresholds, emails
    """
    try:
        headers = {
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{ALERTS_API_URL}/alerts",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        all_alerts = response.json()
        
        # Filter by status if needed
        if status == "active":
            all_alerts = [a for a in all_alerts if a.get("active") == 1]
        
        # Simplify for AI consumption
        simplified = []
        for alert in all_alerts:
            simplified.append({
                "id": alert.get("id"),
                "field_name": alert.get("field_name"),
                "field_id": alert.get("field_id"),
                "alert_type": alert.get("alert_type"),
                "condition": alert.get("condition_type"),
                "threshold": alert.get("threshold_value"),
                "emails": alert.get("notification_emails"),
                "active": bool(alert.get("active"))
            })
        
        return simplified
    
    except Exception as e:
        return {"error": f"Could not fetch alerts: {str(e)}"}


def create_alert_in_system(
    user_context: dict,
    field_name: str,
    alert_type: str,
    threshold: float,
    operator: str,
    email: str
) -> dict:
    """
    Creates a new alert in yieldera-alerts-main system.
    This enables natural language alert creation like "alert me when temp > 40".
    
    Args:
        user_context: User context
        field_name: Name of the field (will be looked up to get ID)
        alert_type: "temperature", "windspeed", "rainfall", or "ndvi"
        threshold: Threshold value (e.g., 40 for temperature)
        operator: ">", "<", ">=", or "<="
        email: Email address for notifications
    
    Returns:
        Success message or error
    """
    try:
        # First, get field ID from field name
        from tools.internal import get_fields_via_bridge
        fields = get_fields_via_bridge(user_context)
        
        if isinstance(fields, dict) and "error" in fields:
            return {"error": "Could not look up fields"}
        
        # Find matching field
        matching_field = None
        for field in fields:
            if field.get("name", "").lower() == field_name.lower():
                matching_field = field
                break
        
        if not matching_field:
            return {"error": f"Field '{field_name}' not found in your portfolio"}
        
        field_id = matching_field["id"]
        
        # Map operator to condition_type
        condition_map = {
            ">": "greater_than",
            ">=": "greater_than",
            "<": "less_than",
            "<=": "less_than",
            "=": "equal_to",
            "==": "equal_to"
        }
        condition_type = condition_map.get(operator, "greater_than")
        
        # Create alert via API
        headers = {
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "field_id": field_id,
            "alert_type": alert_type,
            "condition_type": condition_type,
            "threshold_value": threshold,
            "notification_emails": email,
            "active": 1
        }
        
        response = requests.post(
            f"{ALERTS_API_URL}/alerts",
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "alert_id": result.get("id"),
            "message": f"Created {alert_type} alert for field '{field_name}'. Will notify {email} when {alert_type} {operator} {threshold}"
        }
    
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"error": f"Could not create alert: {str(e)}"}
