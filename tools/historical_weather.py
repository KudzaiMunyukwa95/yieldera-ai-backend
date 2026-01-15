import requests
from typing import Dict, Any, Optional

def get_historical_weather(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    start_date: str = None,
    end_date: str = None,
    field_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetches HISTORICAL weather data using the frost-monitor dual consensus module.
    This uses OpenMeteo + NASA POWER for reliable historical temperature data.
    
    Args:
        lat: Latitude (optional if field_id is provided)
        lon: Longitude (optional if field_id is provided)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        field_id: Field ID to look up coordinates (optional, preferred over lat/lon)
    
    Returns:
        Historical temperature data with dual-source consensus
    """
    try:
        FROST_API_URL = "https://yieldera-frost-monitor.onrender.com"
        
        # Build payload based on what's provided
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "threshold": 0.0,  # Not checking for frost, just getting temps
            "output_type": "daily"
        }
        
        # If field_id is provided, use it (frost API will look up coordinates)
        # Otherwise use lat/lon
        if field_id:
            payload["field_id"] = field_id
            print(f"📡 Requesting historical weather for field_id={field_id} from {start_date} to {end_date}")
        elif lat is not None and lon is not None:
            payload["coordinates"] = {"lat": lat, "lon": lon}
            print(f"📡 Requesting historical weather from {start_date} to {end_date}")
            print(f"📍 Using coordinates: Lat={lat}, Lon={lon}")
        else:
            return {"error": "Either field_id or (lat, lon) must be provided"}
        
        response = requests.post(
            f"{FROST_API_URL}/frost-monitor",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        print(f"🔍 DEBUG: Full API response status: {data.get('status')}")
        print(f"🔍 DEBUG: First 3 daily records: {data.get('results', {}).get('daily', [])[:3]}")
        
        if data.get("status") != "success":
            return {"error": "Failed to retrieve historical weather data"}
        
        # Simplify the response for AI
        daily_records = data.get("results", {}).get("daily", [])
        
        simplified = []
        for record in daily_records:
            # Use consensus between OpenMeteo and NASA (dual consensus module)
            temp_min = record.get("openmeteo_tmin") or record.get("nasa_tmin")
            simplified.append({
                "date": record.get("date"),
                "temp_min_celsius": temp_min,
                "source": record.get("source", "dual_consensus")
            })
        
        # Log min/max to check for sanity
        if simplified:
            temps = [r["temp_min_celsius"] for r in simplified if r["temp_min_celsius"] is not None]
            if temps:
                print(f"🌡️ DEBUG: Temperature range: {min(temps)}°C to {max(temps)}°C")
        
        print(f"✅ Retrieved {len(simplified)} days of historical weather")
        
        location_info = data.get("location", "Unknown")
        
        return {
            "location": location_info,
            "period": f"{start_date} to {end_date}",
            "records_count": len(simplified),
            "data": simplified  # List of daily records with date and temp_min
        }
    
    except requests.exceptions.HTTPError as e:
        print(f"❌ Historical weather API error: {e.response.status_code}")
        return {"error": f"API error: {e.response.status_code}"}
    except Exception as e:
        print(f"❌ Historical weather error: {str(e)}")
        return {"error": f"Failed to fetch historical weather: {str(e)}"}
