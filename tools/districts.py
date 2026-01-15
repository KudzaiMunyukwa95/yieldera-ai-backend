"""
Zimbabwe Districts Lookup for Insurance Quotes
Calculates centroids from district polygons for region-based quotes
Source: yieldera-visualization-main/backend/data/regions.py
"""

from typing import Dict, Optional, Tuple, List

def calculate_polygon_centroid(coordinates: List[List[List[float]]]) -> Tuple[float, float]:
    """
    Calculate centroid of a polygon from coordinates
    
    Args:
        coordinates: GeoJSON polygon coordinates [[[lon, lat], [lon, lat], ...]]
    
    Returns:
        Tuple of (latitude, longitude)
    """
    # Get the outer ring (first element)
    ring = coordinates[0]
    
    # Calculate centroid using average of all points
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    
    centroid_lon = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)
    
    return (centroid_lat, centroid_lon)


# Zimbabwe Districts with calculated centroids
# Extracted from yieldera-visualization-main shapefile data
ZIMBABWE_DISTRICTS = {
    # Mashonaland Central
    "bindura": {"lat": -17.0, "lon": 31.4, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    "centenary": {"lat": -16.1, "lon": 31.1, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    "shamva": {"lat": -17.1, "lon": 31.6, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    "mount darwin": {"lat": -16.4, "lon": 31.3, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    "rushinga": {"lat": -16.6, "lon": 32.1, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    "muzarabani": {"lat": -16.2, "lon": 30.7, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    "guruve": {"lat": -16.8, "lon": 30.9, "province": "Mashonaland Central", "zone": "aez_3_midlands"},
    
    # Mashonaland East
    "mutoko": {"lat": -17.6, "lon": 32.1, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    "mudzi": {"lat": -17.2, "lon": 31.9, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    "chikomba": {"lat": -18.4, "lon": 31.4, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    "marondera": {"lat": -18.3, "lon": 31.7, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    "goromonzi": {"lat": -18.0, "lon": 31.3, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    "seke": {"lat": -18.2, "lon": 31.2, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    "ump": {"lat": -18.6, "lon": 31.9, "province": "Mashonaland East", "zone": "aez_3_midlands"},
    
    # Mashonaland West
    "kadoma": {"lat": -18.5, "lon": 29.9, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    "chinhoyi": {"lat": -17.4, "lon": 30.3, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    "kariba": {"lat": -16.8, "lon": 29.0, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    "hurungwe": {"lat": -17.3, "lon": 29.5, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    "makonde": {"lat": -17.2, "lon": 30.4, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    "zvimba": {"lat": -17.8, "lon": 30.5, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    "chegutu": {"lat": -18.3, "lon": 30.3, "province": "Mashonaland West", "zone": "aez_3_midlands"},
    
    # Manicaland
    "mutare": {"lat": -19.1, "lon": 32.7, "province": "Manicaland", "zone": "aez_3_midlands"},
    "nyanga": {"lat": -18.3, "lon": 32.85, "province": "Manicaland", "zone": "aez_3_midlands"},
    "makoni": {"lat": -18.8, "lon": 32.3, "province": "Manicaland", "zone": "aez_3_midlands"},
    "buhera": {"lat": -19.4, "lon": 32.0, "province": "Manicaland", "zone": "aez_4_masvingo"},
    "chipinge": {"lat": -20.0, "lon": 32.7, "province": "Manicaland", "zone": "aez_4_masvingo"},
    "chimanimani": {"lat": -19.9, "lon": 32.95, "province": "Manicaland", "zone": "aez_4_masvingo"},
    "rusape": {"lat": -19.1, "lon": 32.3, "province": "Manicaland", "zone": "aez_3_midlands"},
    
    # Midlands
    "gweru": {"lat": -19.5, "lon": 29.9, "province": "Midlands", "zone": "aez_3_midlands"},
    "kwekwe": {"lat": -19.1, "lon": 29.9, "province": "Midlands", "zone": "aez_3_midlands"},
    "gokwe north": {"lat": -18.8, "lon": 28.8, "province": "Midlands", "zone": "aez_3_midlands"},
    "gokwe south": {"lat": -19.4, "lon": 29.0, "province": "Midlands", "zone": "aez_3_midlands"},
    "shurugwi": {"lat": -19.8, "lon": 30.3, "province": "Midlands", "zone": "aez_3_midlands"},
    "chirumhanzu": {"lat": -20.0, "lon": 30.5, "province": "Midlands", "zone": "aez_3_midlands"},
    
    # Masvingo
    "masvingo urban": {"lat": -20.3, "lon": 30.9, "province": "Masvingo", "zone": "aez_4_masvingo"},
    "masvingo": {"lat": -20.3, "lon": 30.9, "province": "Masvingo", "zone": "aez_4_masvingo"},  # Alias
    "chiredzi": {"lat": -21.5, "lon": 31.5, "province": "Masvingo", "zone": "aez_5_lowveld"},
    "bikita": {"lat": -20.4, "lon": 31.7, "province": "Masvingo", "zone": "aez_4_masvingo"},
    "zaka": {"lat": -20.8, "lon": 31.5, "province": "Masvingo", "zone": "aez_4_masvingo"},
    "gutu": {"lat": -20.2, "lon": 31.1, "province": "Masvingo", "zone": "aez_4_masvingo"},
    "chivi": {"lat": -20.9, "lon": 30.4, "province": "Masvingo", "zone": "aez_4_masvingo"},
    "mwenezi": {"lat": -21.6, "lon": 30.0, "province": "Masvingo", "zone": "aez_5_lowveld"},
    
    # Matabeleland North
    "hwange": {"lat": -18.6, "lon": 26.4, "province": "Matabeleland North", "zone": "aez_5_lowveld"},
    "binga": {"lat": -17.4, "lon": 27.5, "province": "Matabeleland North", "zone": "aez_5_lowveld"},
    "lupane": {"lat": -18.7, "lon": 28.1, "province": "Matabeleland North", "zone": "aez_5_lowveld"},
    "nkayi": {"lat": -19.0, "lon": 28.8, "province": "Matabeleland North", "zone": "aez_5_lowveld"},
    "tsholotsho": {"lat": -19.4, "lon": 27.9, "province": "Matabeleland North", "zone": "aez_5_lowveld"},
    
    # Matabeleland South
    "gwanda": {"lat": -21.0, "lon": 29.4, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
    "beitbridge": {"lat": -22.1, "lon": 30.0, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
    "matobo": {"lat": -20.6, "lon": 28.6, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
    "mangwe": {"lat": -21.0, "lon": 28.2, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
    "bulilima": {"lat": -21.3, "lon": 26.9, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
    "insiza": {"lat": -20.4, "lon": 29.2, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
    "umzingwane": {"lat": -20.8, "lon": 29.0, "province": "Matabeleland South", "zone": "aez_5_lowveld"},
}


def get_district_info(region_name: str) -> Optional[Dict]:
    """
    Get district information by name with fuzzy matching
    
    Args:
        region_name: District name (case-insensitive, supports variations)
    
    Returns:
        District info dict with lat, lon, province, zone or None if not found
    """
    # Normalize input
    clean_name = region_name.lower().strip()
    
    # Remove common suffixes
    for suffix in [' district', ' rural', ' urban', ' metropolitan']:
        clean_name = clean_name.replace(suffix, '')
    clean_name = clean_name.strip()
    
    # Try exact match first
    if clean_name in ZIMBABWE_DISTRICTS:
        district = ZIMBABWE_DISTRICTS[clean_name]
        return {
            "name": region_name,
            "latitude": district["lat"],
            "longitude": district["lon"],
            "province": district["province"],
            "zone": district["zone"]
        }
    
    # Try fuzzy matching
    for district_key, district_info in ZIMBABWE_DISTRICTS.items():
        # Check if search term is in district name or vice versa
        if clean_name in district_key or district_key in clean_name:
            if len(clean_name) >= 3:  # Avoid matching on very short strings
                return {
                    "name": district_key.title(),
                    "latitude": district_info["lat"],
                    "longitude": district_info["lon"],
                    "province": district_info["province"],
                    "zone": district_info["zone"]
                }
    
    return None


def list_all_districts() -> List[str]:
    """Get list of all supported district names"""
    return sorted([key.title() for key in ZIMBABWE_DISTRICTS.keys()])


def get_districts_by_province(province_name: str) -> List[Dict]:
    """Get all districts in a specific province"""
    districts = []
    for name, info in ZIMBABWE_DISTRICTS.items():
        if province_name.lower() in info["province"].lower():
            districts.append({
                "name": name.title(),
                "latitude": info["lat"],
                "longitude": info["lon"],
                "zone": info["zone"]
            })
    return districts
