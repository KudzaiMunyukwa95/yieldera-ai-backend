import requests
from typing import Dict, Any, Optional

INDEX_API_URL = "https://yieldera-index.onrender.com"

def get_insurance_quote(
    user_context: dict,
    quote_type: str,
    field_id: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    region_name: Optional[str] = None,
    expected_yield: float = 5.0,
    price_per_ton: float = 300.0,
    year: Optional[int] = None,
    crop: str = "maize",
    deductible_rate: float = 0.05,
    area_ha: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate actuarial insurance quotes for agricultural coverage.
    
    IMPORTANT: When presenting the quote to the user, YOU MUST prominently display the PDF download link
    from the 'pdf_download_url' field at the top of your response. Format it as a clickable link like:
    
    📄 **Download Full PDF Report**: [Click here to download](https://yieldera.net/dashboard/pricing.html?quote_id=XXX)
    
    Args:
        user_context: User authentication context
        quote_type: One of "field", "coordinates", or "region"
        field_id: Field ID (required if quote_type="field")
        latitude: Latitude (required if quote_type="coordinates")
        longitude: Longitude (required if quote_type="coordinates")
        region_name: Region name like "Mazowe" (required if quote_type="region")
        expected_yield: Expected yield in tons/ha (default: 5.0)
        price_per_ton: Price per ton in $ (default: 300)
        year: Quote year (defaults to next season)
        crop: Crop type (default: "maize")
        deductible_rate: Deductible percentage (default: 0.05 = 5%)
        area_ha: Area in hectares (optional)
    
    Returns:
        Quote result with premium, sum insured, and AI summary
    """
    try:
        from datetime import datetime
        
        # Default to next season if no year provided
        if year is None:
            current_month = datetime.now().month
            current_year = datetime.now().year
            year = current_year + 1 if current_month >= 8 else current_year
        
        print(f"[QUOTE] Generating {quote_type} insurance quote for {year}")
        
        # PROGRESS MESSAGE: Inform user about processing time
        print("\n" + "="*60)
        print("ACTUARIAL QUOTE PROCESSING")
        print("="*60)
        print(f"Location Type: {quote_type.title()}")
        print(f"Coverage Year: {year}")
        print(f"\nEstimated Processing Time: 60-90 seconds")
        print("\nWhat's Happening:")
        print("  [1/3] Detecting optimal planting windows...")
        print("  [2/3] Analyzing 20+ years of rainfall data...")
        print("  [3/3] Calculating risk-adjusted premium rates...")
        print("\nPlease wait while we analyze satellite data from Google Earth Engine")
        print("="*60 + "\n")
        
        # Route to appropriate endpoint based on quote type
        if quote_type == "field":
            if field_id is None:
                return {"error": "field_id is required for field-based quotes"}
            
            return _get_field_quote(
                field_id, expected_yield, price_per_ton, year, 
                deductible_rate, area_ha
            )
        
        elif quote_type == "coordinates":
            if latitude is None or longitude is None:
                return {"error": "latitude and longitude are required for coordinate-based quotes"}
            
            return _get_coordinate_quote(
                latitude, longitude, expected_yield, price_per_ton, 
                year, crop, deductible_rate, area_ha
            )
        
        elif quote_type == "region":
            if region_name is None:
                return {"error": "region_name is required for region-based quotes"}
            
            # Look up district coordinates
            from tools.districts import get_district_info
            
            district_info = get_district_info(region_name)
            
            if not district_info:
                # Provide helpful error with available districts
                from tools.districts import list_all_districts
                available = list_all_districts()
                return {
                    "error": f"District '{region_name}' not found. Available districts: {', '.join(available[:10])}... (and {len(available) - 10} more)"
                }
            
            print(f"[REGION] Found district: {district_info['name']} in {district_info['province']}")
            print(f"[REGION] Using coordinates: {district_info['latitude']}, {district_info['longitude']}")
            print(f"[REGION] Agroecological zone: {district_info['zone']}")
            
            # Use coordinate-based quote with district centroid
            result = _get_coordinate_quote(
                district_info['latitude'], 
                district_info['longitude'],
                expected_yield, 
                price_per_ton,
                year, 
                crop, 
                deductible_rate, 
                area_ha
            )
            
            # Update result to show district name instead of coordinates
            if "status" in result and result["status"] == "success":
                result["quote_type"] = "region"
                result["location"] = f"{district_info['name']} District, {district_info['province']}"
                result["district_info"] = district_info
            
            return result
        
        else:
            return {"error": f"Invalid quote_type: {quote_type}. Use 'field', 'coordinates', or 'region'"}
    
    except Exception as e:
        print(f"[ERROR] Insurance quote error: {str(e)}")
        return {"error": f"Failed to generate quote: {str(e)}"}


def _get_field_quote(field_id, expected_yield, price_per_ton, year, deductible_rate, area_ha):
    """Generate quote for a specific field"""
    try:
        payload = {
            "expected_yield": expected_yield,
            "price_per_ton": price_per_ton,
            "year": year,
            "deductible_rate": deductible_rate
        }
        
        if area_ha:
            payload["area_ha"] = area_ha
        
        print(f"[FIELD] Requesting quote for field_id={field_id}")
        
        response = requests.post(
            f"{INDEX_API_URL}/api/quotes/field/{field_id}",
            json=payload,
            timeout=120  # Increased from 30 to 120 seconds for Earth Engine processing
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "success":
            quote = data.get("quote", {})
            quote_id = quote.get("quote_id")
            
            # Generate DIRECT PDF download URL (backend endpoint)
            pdf_url = f"https://yieldera-index.onrender.com/api/quotes/{quote_id}/pdf" if quote_id else None
            
            field_data = data.get("field_data", {})
            
            return {
                "status": "success",
                "quote_type": "field",
                "field_id": field_id,
                "field_name": field_data.get("name", f"Field {field_id}"),
                "sum_insured": f"${quote.get('sum_insured', 0):,.2f}",
                "gross_premium": f"${quote.get('gross_premium', 0):,.2f}",
                "premium_rate": f"{quote.get('premium_rate', 0) * 100:.2f}%",
                "deductible": f"{deductible_rate * 100}%",
                "ai_summary": quote.get("ai_summary", "Summary not available"),
                "quote_id": quote_id,
                "pdf_download_url": pdf_url,
                "execution_time": data.get("execution_time_seconds"),
                "raw_quote": quote  # Full quote data for advanced display
            }
        else:
            return {"error": data.get("message", "Quote generation failed")}
    
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


def _get_coordinate_quote(lat, lon, expected_yield, price_per_ton, year, crop, deductible_rate, area_ha):
    """Generate quote for GPS coordinates"""
    try:
        payload = {
            "latitude": lat,
            "longitude": lon,
            "expected_yield": expected_yield,
            "price_per_ton": price_per_ton,
            "year": year,
            "crop": crop,
            "deductible_rate": deductible_rate
        }
        
        if area_ha:
            payload["area_ha"] = area_ha
        
        print(f"[GPS] Requesting quote for coordinates ({lat}, {lon})")
        
        # Use prospective endpoint for future years
        response = requests.post(
            f"{INDEX_API_URL}/api/quotes/prospective",
            json=payload,
            timeout=120  # Increased from 30 to 120 seconds for Earth Engine processing
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "success":
            quote = data.get("quote", {})
            quote_id = quote.get("quote_id")
            
            # Generate DIRECT PDF download URL (backend endpoint)
            pdf_url = f"https://yieldera-index.onrender.com/api/quotes/{quote_id}/pdf" if quote_id else None
            
            return {
                "status": "success",
                "quote_type": "coordinates",
                "location": f"Lat: {lat}, Lon: {lon}",
                "sum_insured": f"${quote.get('sum_insured', 0):,.2f}",
                "gross_premium": f"${quote.get('gross_premium', 0):,.2f}",
                "premium_rate": f"{quote.get('premium_rate', 0) * 100:.2f}%",
                "deductible": f"{deductible_rate * 100}%",
                "ai_summary": quote.get("ai_summary", "Summary not available"),
                "quote_id": quote_id,
                "pdf_download_url": pdf_url,
                "execution_time": data.get("execution_time_seconds"),
                "raw_quote": quote
            }
        else:
            return {"error": data.get("message", "Quote generation failed")}
    
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def _get_region_quote(region_name, expected_yield, price_per_ton, year, crop, deductible_rate, area_ha):
    """Generate quote for a named region (uses shapefile)"""
    try:
        payload = {
            "region": region_name,
            "expected_yield": expected_yield,
            "price_per_ton": price_per_ton,
            "year": year,
            "crop": crop,
            "deductible_rate": deductible_rate
        }
        
        if area_ha:
            payload["area_ha"] = area_ha
        
        print(f"[REGION] Requesting quote for region: {region_name}")
        
        # Use PROSPECTIVE endpoint (historical is for past years only)
        response = requests.post(
            f"{INDEX_API_URL}/api/quotes/prospective",
            json=payload,
            timeout=120  # Increased from 30 to 120 seconds for Earth Engine processing
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "success":
            quote = data.get("quote", {})
            
            return {
                "status": "success",
                "quote_type": "region",
                "location": region_name,
                "sum_insured": f"${quote.get('sum_insured', 0):,.2f}",
                "gross_premium": f"${quote.get('gross_premium', 0):,.2f}",
                "premium_rate": f"{quote.get('premium_rate', 0) * 100:.2f}%",
                "deductible": f"{deductible_rate * 100}%",
                "ai_summary": quote.get("ai_summary", "Summary not available"),
                "quote_id": quote.get("quote_id"),
                "execution_time": data.get("execution_time_seconds"),
                "raw_quote": quote
            }
        else:
            return {"error": data.get("message", "Quote generation failed")}
    
    except requests.exceptions.HTTPError as e:
        return {"error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}
