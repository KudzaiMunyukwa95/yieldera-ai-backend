import requests
from typing import Dict, Any

def get_historical_weather(lat: float, lon: float, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Fetches HISTORICAL weather data using the frost-monitor dual consensus module.
    This uses OpenMeteo + NASA POWER for reliable historical temperature data.
    
    Args:
        lat: Latitude
        lon: Longitude  
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Historical temperature data with dual-source consensus
    """
    try:
        FROST_API_URL = "https://yieldera-frost-monitor.onrender.com"
        
        payload = {
            "coordinates": {"lat": lat, "lon": lon},
            "start_date": start_date,
            "end_date": end_date,
            "threshold": 0.0,  # Not checking for frost, just getting temps
            "output_type": "daily"
        }
        
        print(f"📡 Requesting historical weather from {start_date} to {end_date}")
        
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
        
        return {
            "location": f"Lat: {lat}, Lon: {lon}",
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
