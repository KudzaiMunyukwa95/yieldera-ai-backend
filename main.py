from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import logging

from openmeteo import get_openmeteo_data
from nasa_power import get_nasa_power_data
from db import get_field_by_id, get_user_fields
from utils import validate_coordinates, calculate_consensus, aggregate_monthly

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Yieldera Frost Monitor"})

@app.route('/frost-monitor', methods=['POST'])
def frost_monitor():
    """
    Main frost monitoring endpoint
    Expected JSON payload:
    {
        "coordinates": [[lat, lon], [lat, lon], ...] or {"lat": float, "lon": float},
        "field_id": int (optional),
        "threshold": float (default 0),
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "output_type": "daily" | "monthly" | "both" (default "both")
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400
        
        # Handle coordinates or field_id
        coordinates = None
        if 'field_id' in data:
            field = get_field_by_id(data['field_id'])
            if not field:
                return jsonify({"error": "Field not found"}), 404
            coordinates = field['coordinates']
        elif 'coordinates' in data:
            coordinates = data['coordinates']
        else:
            return jsonify({"error": "Either coordinates or field_id must be provided"}), 400
        
        # Validate coordinates
        if not validate_coordinates(coordinates):
            return jsonify({"error": "Invalid coordinates format"}), 400
        
        # Extract parameters
        threshold = data.get('threshold', 0.0)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        output_type = data.get('output_type', 'both')
        
        # Validate dates
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date are required"}), 400
        
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        if start_dt >= end_dt:
            return jsonify({"error": "start_date must be before end_date"}), 400
        
        # Check date range (limit to 2 years for performance)
        if (end_dt - start_dt).days > 730:
            return jsonify({"error": "Date range cannot exceed 2 years"}), 400
        
        logger.info(f"Processing frost data for period {start_date} to {end_date}")
        
        # Get data from both sources: Open Meteo + NASA POWER
        openmeteo_data = get_openmeteo_data(coordinates, start_date, end_date)
        nasa_data = get_nasa_power_data(coordinates, start_date, end_date)
        
        # Check if we have at least one data source
        if not nasa_data and not openmeteo_data:
            return jsonify({"error": "Failed to retrieve data from both sources"}), 500
        
        if not openmeteo_data and nasa_data:
            logger.warning("Open Meteo data unavailable, using NASA POWER only")
            # Use NASA data only
            daily_results = []
            for record in nasa_data:
                daily_results.append({
                    'date': record['date'],
                    'openmeteo_tmin': None,
                    'nasa_tmin': record['tmin'],
                    'openmeteo_frost': None,
                    'nasa_frost': record['tmin'] <= threshold,
                    'consensus': record['tmin'] <= threshold,
                    'source': 'nasa_only'
                })
        elif not nasa_data and openmeteo_data:
            logger.warning("NASA POWER data unavailable, using Open Meteo only")
            # Use Open Meteo data only
            daily_results = []
            for record in openmeteo_data:
                daily_results.append({
                    'date': record['date'],
                    'openmeteo_tmin': record['tmin'],
                    'nasa_tmin': None,
                    'openmeteo_frost': record['tmin'] <= threshold,
                    'nasa_frost': None,
                    'consensus': record['tmin'] <= threshold,
                    'source': 'openmeteo_only'
                })
        else:
            # Calculate consensus with both sources
            daily_results = calculate_consensus(openmeteo_data, nasa_data, threshold, 'openmeteo')
        
        monthly_summary = aggregate_monthly(daily_results)
        total_frost_days = sum(1 for day in daily_results if day['consensus'])
        
        # Determine location info
        if isinstance(coordinates, list) and len(coordinates) > 2:
            # Polygon - calculate centroid
            lats = [coord[0] for coord in coordinates]
            lons = [coord[1] for coord in coordinates]
            location = f"Polygon centroid: {sum(lats)/len(lats):.4f}, {sum(lons)/len(lons):.4f}"
        else:
            # Point coordinates
            if isinstance(coordinates, dict):
                location = f"Point: {coordinates['lat']}, {coordinates['lon']}"
            else:
                location = f"Point: {coordinates[0]}, {coordinates[1]}"
        
        # Prepare response based on output_type
        results = {}
        if output_type in ['daily', 'both']:
            results['daily'] = daily_results
        if output_type in ['monthly', 'both']:
            results['monthly_summary'] = monthly_summary
            results['total_frost_days'] = total_frost_days
        
        return jsonify({
            "status": "success",
            "location": location,
            "threshold": threshold,
            "period": f"{start_date} to {end_date}",
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error in frost_monitor: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/frost-summary', methods=['GET'])
def frost_summary():
    """
    Quick 12-month frost overview
    Query parameters:
    - lat, lon: coordinates
    - field_id: alternative to lat/lon
    - threshold: frost threshold (default 0)
    - year: year for analysis (default current year)
    """
    try:
        # Get coordinates
        field_id = request.args.get('field_id')
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        coordinates = None
        if field_id:
            field = get_field_by_id(int(field_id))
            if not field:
                return jsonify({"error": "Field not found"}), 404
            coordinates = field['coordinates']
        elif lat is not None and lon is not None:
            coordinates = {"lat": lat, "lon": lon}
        else:
            return jsonify({"error": "Either field_id or lat/lon must be provided"}), 400
        
        threshold = request.args.get('threshold', 0.0, type=float)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Calculate 12-month period
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        logger.info(f"Generating frost summary for {year}")
        
        # Get data from both sources with fallback logic
        openmeteo_data = get_openmeteo_data(coordinates, start_date, end_date)
        nasa_data = get_nasa_power_data(coordinates, start_date, end_date)
        
        if not nasa_data and not openmeteo_data:
            return jsonify({"error": "Failed to retrieve data from both sources"}), 500
        
        # Calculate consensus (with fallback to single source)
        if openmeteo_data and nasa_data:
            daily_results = calculate_consensus(openmeteo_data, nasa_data, threshold, 'openmeteo')
        elif openmeteo_data:
            daily_results = calculate_consensus(None, openmeteo_data, threshold, 'openmeteo')
        else:
            daily_results = calculate_consensus(None, nasa_data, threshold, 'nasa')
        monthly_summary = aggregate_monthly(daily_results)
        total_frost_days = sum(1 for day in daily_results if day['consensus'])
        
        return jsonify({
            "status": "success",
            "year": year,
            "threshold": threshold,
            "monthly_summary": monthly_summary,
            "total_frost_days": total_frost_days,
            "location": f"Point: {coordinates.get('lat', 'N/A')}, {coordinates.get('lon', 'N/A')}"
        })
        
    except Exception as e:
        logger.error(f"Error in frost_summary: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/user-fields/<int:user_id>', methods=['GET'])
def user_fields(user_id):
    """Get all fields for a specific user"""
    try:
        fields = get_user_fields(user_id)
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "fields": fields
        })
    except Exception as e:
        logger.error(f"Error getting user fields: {str(e)}")
        return jsonify({"error": f"Failed to retrieve user fields: {str(e)}"}), 500

@app.route('/test-openmeteo', methods=['POST'])
def test_openmeteo():
    """Test Open Meteo API data retrieval"""
    try:
        data = request.get_json()
        coordinates = data.get('coordinates', {"lat": -17.8252, "lon": 31.0335})
        start_date = data.get('start_date', '2024-07-15')
        end_date = data.get('end_date', '2024-07-20')
        
        openmeteo_data = get_openmeteo_data(coordinates, start_date, end_date)
        
        return jsonify({
            "status": "success" if openmeteo_data else "failed",
            "source": "Open Meteo",
            "records_count": len(openmeteo_data) if openmeteo_data else 0,
            "data": openmeteo_data[:5] if openmeteo_data else None,  # First 5 records
            "coordinates": coordinates,
            "date_range": f"{start_date} to {end_date}"
        })
    except Exception as e:
        logger.error(f"Error testing Open Meteo: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-services', methods=['GET'])
def test_services():
    """Test both Open Meteo and NASA POWER API services"""
    try:
        from openmeteo import test_openmeteo_api, get_openmeteo_info
        from nasa_power import test_nasa_api
        
        # Test both services
        openmeteo_status = test_openmeteo_api()
        nasa_status = test_nasa_api()
        
        return jsonify({
            "status": "success" if (openmeteo_status and nasa_status) else "partial",
            "services": {
                "open_meteo": {
                    "available": openmeteo_status,
                    "info": get_openmeteo_info()
                },
                "nasa_power": {
                    "available": nasa_status,
                    "description": "NASA POWER Global Meteorology Data"
                }
            },
            "dual_source_available": openmeteo_status and nasa_status
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e),
            "services_available": False
        })
def test_nasa():
    """Test NASA POWER API data retrieval"""
    try:
        data = request.get_json()
        coordinates = data.get('coordinates', {"lat": -17.8252, "lon": 31.0335})
        start_date = data.get('start_date', '2024-07-15')
        end_date = data.get('end_date', '2024-07-20')
        
        nasa_data = get_nasa_power_data(coordinates, start_date, end_date)
        
        return jsonify({
            "status": "success" if nasa_data else "failed",
            "source": "NASA POWER",
            "records_count": len(nasa_data) if nasa_data else 0,
            "data": nasa_data[:5] if nasa_data else None,  # First 5 records
            "coordinates": coordinates,
            "date_range": f"{start_date} to {end_date}"
        })
    except Exception as e:
        logger.error(f"Error testing NASA: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
