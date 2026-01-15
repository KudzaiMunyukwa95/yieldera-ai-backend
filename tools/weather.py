import requests
from integrations.redis_cache import cache
from core.audit import AuditLog

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def get_weather_forecast(lat: float, lon: float, days: int = 7) -> dict:
    """
    Fetches weather forecast from OpenMeteo with Caching.
    CACHE KEY: `weather:{lat}:{lon}`
    TTL: 4 Hours
    """
    # 1. Check Cache
    cache_key = f"weather:{round(lat, 2)}:{round(lon, 2)}"
    cached_data = cache.get_json(cache_key)
    
    if cached_data:
        AuditLog.log_event("system", "CACHE_HIT", {"tool": "weather", "key": cache_key})
        return cached_data

    # 2. Fetch Live Data
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": days
    }
    
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # 3. Simplify Response for AI (Token economy)
        daily = data.get("daily", {})
        simplified = {
            "dates": daily.get("time", []),
            "max_temp": daily.get("temperature_2m_max", []),
            "min_temp": daily.get("temperature_2m_min", []),
            "rain_mm": daily.get("precipitation_sum", []),
            "rain_prob": daily.get("precipitation_probability_max", [])
        }
        
        result = {
            "location": {"lat": lat, "lon": lon},
            "forecast": simplified,
            "units": data.get("daily_units", {})
        }

        # 4. Save to Cache (4 Hours)
        cache.set_json(cache_key, result, ttl_seconds=14400)
        AuditLog.log_event("system", "API_CALL", {"tool": "weather", "status": "success"})
        
        return result

    except Exception as e:
        AuditLog.log_event("system", "TOOL_ERROR", {"tool": "weather", "error": str(e)})
        return {"error": "Weather service unavailable", "details": str(e)}
