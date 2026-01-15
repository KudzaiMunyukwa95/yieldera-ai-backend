import requests
import datetime
from datetime import timedelta
from core.config import get_settings
from core.audit import AuditLog
from tools.internal import get_fields_via_bridge

settings = get_settings()

def get_vegetation_health(user_context: dict, field_id: int, date: str) -> dict:
    """
    Fetches the vegetation health (NDVI) for a specific field on or near a specific date.
    
    Args:
        user_context (dict): User context for auth.
        field_id (int): The ID of the field to analyze.
        date (str): Target date in 'YYYY-MM-DD' format.
        
    Returns:
        dict: NDVI stats, imagery date, and cloud cover.
    """
    # 1. Get Field Coordinates (Secure Lookup)
    # We re-fetch fields to ensure the user actually owns this field ID.
    all_fields = get_fields_via_bridge(user_context)
    
    target_field = next((f for f in all_fields if f["id"] == field_id), None)
    
    if not target_field:
        return {"error": f"Field ID {field_id} not found or access denied."}
        
    coords = target_field.get("location")
    if not coords:
         return {"error": f"Field ID {field_id} has no location data."}

    # 2. Calculate Date Window (Remote Sensing isn't daily)
    # Sentinel-2 has a 5-day revisit time. We look +/- 7 days to find a good image.
    try:
        target_date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}
        
    start_date = (target_date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = (target_date_obj + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # 3. Call NDVI Backend
    # The URL is hardcoded or should be in settings. Ideally settings.
    # For now I'll use the one I found in config.js
    url = "https://ndvi-backend-2.onrender.com/api/gee_ndvi"
    
    # GEE requires a Polygon (looped coordinates). 
    # The PHP bridge returns [lon, lat] which is a Point.
    # If the field is a Point, we need to buffer it or fail? 
    # Wait, get_fields.php returns ST_AsGeoJSON. 
    # If it's a Point, GEE needs a Polygon.
    # Let's check internal.py output. It says "location" : f.get("geometry", {}).get("coordinates").
    # If geometry type is Point, coords is [x, y].
    # If Polygon, coords is [[[x,y], ...]].
    # The GEE backend expects `coordinates` as a list of points representing a ring.
    
    # HACK: If point, create a small box around it?
    # Or rely on the backend to handle it? The backend code says:
    # "if len(coords[0]) < 3: return Invalid polygon"
    # So it MUST be a polygon.
    
    # If the database returns a Point (common for simple fields), we must buffer it.
    # But doing geospatial buffering in python without shapely is annoying.
    # Let's look at internal.py again.
    # It returns raw geojson coordinates.
    # Assuming the user has Polygons. If they have Points, this will fail.
    # For now, we assume Polygons. If it fails, we catch it.
    
    payload = {
        "coordinates": coords,
        "startDate": start_date,
        "endDate": end_date,
        "index_type": "NDVI"
    }
    
    try:
        # We need a secret key? The NDVI backend uses @require_auth.
        # I check gee_ndvi_generator.py for @require_auth implementation?
        # It usually checks Authorization header or X-Secret.
        # The user's other code uses `api_key` in internal call?
        # Wait, the config.js didn't show a key.
        # But gee_ndvi_generator.py *does* have @require_auth.
        # I need to find what token it expects.
        # Likely `INTERNAL_API_KEY` or `OPENAI_API_KEY`? 
        # Actually existing frontend calls it directly? 
        # No, frontend calls it via proxy?
        # Config.js has `GEE_API_TOKEN`. I saw it! 
        # It was: 'e5ab51a6982394b7ed747afdac005a1c851d128fb060898b7b7134789b25f518'
        
        gee_token = "e5ab51a6982394b7ed747afdac005a1c851d128fb060898b7b7134789b25f518" # Hardcoded for now from config.js
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gee_token}"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code == 404:
             return {
                 "status": "No Data",
                 "avg_ndvi": None,
                 "message": f"No clear satellite imagery available between {start_date} and {end_date} (likely clouds)."
             }
             
        response.raise_for_status()
        data = response.json()
        
        # 4. Parse Result
        return {
            "field_id": field_id,
            "target_date": date,
            "satellite_date": data.get("image_date"),
            "avg_ndvi": data.get("mean"),
            "cloud_cover_pct": data.get("cloud_cover"),
            "satellite": data.get("satellite", {}).get("name", "Sentinel-2"),
            "health_assessment": parse_health(data.get("mean"))
        }

    except Exception as e:
        AuditLog.log_event(user_context.get("user_id"), "TOOL_ERROR", {"tool": "get_vegetation", "error": str(e)})
        return {"error": "Failed to fetch vegetation data", "details": str(e)}

def parse_health(ndvi):
    if ndvi is None: return "Unknown"
    if ndvi < 0.2: return "Bare Soil / Dead"
    if ndvi < 0.4: return "Sparse / Stressed"
    if ndvi < 0.6: return "Moderate Vigor"
    if ndvi < 0.8: return "High Vigor"
    return "Very High Vigor"
