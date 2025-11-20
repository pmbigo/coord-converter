from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import json
import os
from .converters import CoordinateConverter
from .schemas import *
from .config import settings
from .logger import logger, log_conversion

app = FastAPI(title=settings.app_name, version="2.0.0")
converter = CoordinateConverter()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("app/static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/convert/point", response_model=PointResponse)
async def convert_point(request: ConversionRequest, http_request: Request):
    """Convert single coordinate point"""
    try:
        # Parse input coordinate
        lon_4326 = converter.parse_dms_to_decimal(request.longitude, request.lon_format)
        lat_4326 = converter.parse_dms_to_decimal(request.latitude, request.lat_format)
        
        # Transform coordinates
        easting, northing = converter.transform_4326_to_21037(lat_4326, lon_4326)
        
        result = PointResponse(
            easting=round(easting, 3),
            northing=round(northing, 3),
            input_lat=request.latitude,
            input_lon=request.longitude
        )
        
        # Log the conversion
        log_conversion(
            original_coords={"lat": request.latitude, "lon": request.longitude},
            converted_coords={"easting": result.easting, "northing": result.northing},
            conversion_type="4326_to_21037",
            user_agent=http_request.headers.get("user-agent", "Unknown")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Point conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")

@app.post("/convert/reverse", response_model=ReversePointResponse)
async def convert_reverse(request: ReverseConversionRequest, http_request: Request):
    """Convert from UTM 21037 to WGS84 4326"""
    try:
        # Transform coordinates
        lat, lon = converter.transform_21037_to_4326(request.easting, request.northing)
        
        # Convert to different formats
        lat_dms = converter.decimal_to_dms(lat, "lat")
        lon_dms = converter.decimal_to_dms(lon, "lon")
        
        result = ReversePointResponse(
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            latitude_dms=lat_dms,
            longitude_dms=lon_dms,
            input_easting=request.easting,
            input_northing=request.northing
        )
        
        # Log the conversion
        log_conversion(
            original_coords={"easting": request.easting, "northing": request.northing},
            converted_coords={"lat": result.latitude, "lon": result.longitude},
            conversion_type="21037_to_4326",
            user_agent=http_request.headers.get("user-agent", "Unknown")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Reverse conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Reverse conversion error: {str(e)}")

@app.post("/convert/batch")
async def convert_batch(
    file: UploadFile = File(...),
    output_format: str = Form("csv"),
    conversion_direction: str = Form("to_utm")  # Only to_utm and to_wgs84 now
):
    """Enhanced batch conversion - supports both directions and Map visualization"""
    logger.info(f"Batch conversion started for file: {file.filename}, format: {output_format}, direction: {conversion_direction}")
    
    try:
        # Read the file content
        contents = await file.read()
        
        # Try multiple encodings to handle the file correctly
        content_str = None
        for encoding in ['utf-8', 'latin-1', 'windows-1252', 'cp1252']:
            try:
                content_str = contents.decode(encoding)
                logger.info(f"Successfully decoded with {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if content_str is None:
            # If all encodings fail, use utf-8 with errors ignored
            content_str = contents.decode('utf-8', errors='ignore')
            logger.info("Used utf-8 with errors ignored")
        
        # Clean common encoding artifacts
        cleaning_replacements = [
            ('Â°', '°'),  # Common UTF-8 misinterpretation
            ('Ã‚Â°', '°'), # Double encoding issue
            ('â€¯', ' '),  # Other common artifacts
            ('â€™', "'"),  # Apostrophe issues
        ]
        
        for wrong, correct in cleaning_replacements:
            content_str = content_str.replace(wrong, correct)
        
        df = pd.read_csv(io.StringIO(content_str))
        lat_col, lon_col, lat_format_col, lon_format_col = detect_csv_columns(df)
        logger.info(f"Detected columns - lat_col: {lat_col}, lon_col: {lon_col}, lat_format_col: {lat_format_col}, lon_format_col: {lon_format_col}")
        
        # Use flexible column detection
        lat_col, lon_col, lat_format_col, lon_format_col = detect_csv_columns(df)
        
        # Validate that we found coordinate columns
        if not lat_col or not lon_col:
            possible_lat_names = ['latitude', 'lat', 'y', 'northing', 'y_coordinate']
            possible_lon_names = ['longitude', 'lon', 'long', 'x', 'easting', 'x_coordinate']
            raise HTTPException(
                status_code=400, 
                detail=f"Could not find coordinate columns. Tried: {possible_lat_names} and {possible_lon_names}. Found columns: {df.columns.tolist()}"
            )
        
        # Process each row
        results = []
        map_points = []
        successful_count = 0
        
        for index, row in df.iterrows():
            try:
                # Get coordinate values
                lat_val = row[lat_col] if lat_col in df.columns else lat_col
                lon_val = row[lon_col] if lon_col in df.columns else lon_col
                
                # Skip empty rows
                if pd.isna(lat_val) or pd.isna(lon_val):
                    result_row = {
                        'original_row': index + 1,
                        'status': 'skipped: empty coordinates',
                        **{col: row[col] for col in df.columns if col in row}
                    }
                    results.append(result_row)
                    continue
                
                # Get and clean the input coordinates
                lat_input = str(lat_val)
                lon_input = str(lon_val)
                
                # Apply cleaning to individual fields
                for wrong, correct in cleaning_replacements:
                    lat_input = lat_input.replace(wrong, correct)
                    lon_input = lon_input.replace(wrong, correct)
                
                if conversion_direction == "to_utm":
                    # 4326 → 21037 conversion
                    lat_format_val = row[lat_format_col] if lat_format_col in df.columns else lat_format_col
                    lon_format_val = row[lon_format_col] if lon_format_col in df.columns else lon_format_col
                    
                    lat_format = str(lat_format_val).strip()
                    lon_format = str(lon_format_val).strip()
                    
                    # Parse coordinates
                    lat_dd = converter.parse_dms_to_decimal(lat_input, lat_format)
                    lon_dd = converter.parse_dms_to_decimal(lon_input, lon_format)
                    
                    # Transform coordinates
                    easting, northing = converter.transform_4326_to_21037(lat_dd, lon_dd)
                    
                    # Create result
                    result_row = {
                        'original_row': index + 1,
                        'input_latitude': lat_input,
                        'input_longitude': lon_input,
                        'latitude_dd': round(lat_dd, 6),
                        'longitude_dd': round(lon_dd, 6),
                        'easting_21037': round(easting, 3),
                        'northing_21037': round(northing, 3),
                        'status': 'success',
                        'conversion_type': '4326_to_21037',
                        **{col: row[col] for col in df.columns if col in row}
                    }
                    
                    # Add to map points
                    map_lat = lat_dd
                    map_lon = lon_dd
                    
                else:  # to_wgs84
                    # 21037 → 4326 conversion
                    try:
                        easting = float(lon_input)  # UTM easting is typically in latitude column
                        northing = float(lat_input)  # UTM northing is typically in longitude column
                        
                        # Transform coordinates
                        lat, lon = converter.transform_21037_to_4326(easting, northing)
                        
                        # Convert to DMS for display
                        lat_dms = converter.decimal_to_dms(lat, "lat")
                        lon_dms = converter.decimal_to_dms(lon, "lon")
                        
                        # Create result
                        result_row = {
                            'original_row': index + 1,
                            'input_easting': easting,
                            'input_northing': northing,
                            'latitude_dd': round(lat, 6),
                            'longitude_dd': round(lon, 6),
                            'latitude_dms': lat_dms,
                            'longitude_dms': lon_dms,
                            'status': 'success',
                            'conversion_type': '21037_to_4326',
                            **{col: row[col] for col in df.columns if col in row}
                        }
                        
                        # Add to map points
                        map_lat = lat
                        map_lon = lon
                        
                    except ValueError as e:
                        raise ValueError(f"Invalid UTM coordinates: {lat_input}, {lon_input}")
                
                results.append(result_row)
                successful_count += 1
                
                # Add to map points for visualization
                point_name = f"Point {index + 1}"
                # Try to get a meaningful name from the data
                for name_col in ['name', 'id', 'description', 'site']:
                    if name_col in df.columns and not pd.isna(row.get(name_col)):
                        point_name = str(row[name_col])
                        break
                
                map_points.append({
                    'name': point_name,
                    'lat': map_lat,
                    'lon': map_lon,
                    'row_number': index + 1,
                    'conversion_type': conversion_direction
                })
                
            except Exception as e:
                error_msg = f"error: {str(e)}"
                result_row = {
                    'original_row': index + 1,
                    'status': error_msg,
                    'conversion_type': conversion_direction,
                    **{col: row[col] for col in df.columns if col in row}
                }
                results.append(result_row)
                logger.warning(f"Row {index} failed: {str(e)}")
        
        logger.info(f"Batch conversion completed. Successful: {successful_count}/{len(results)}")
        
        # Choose output format
        if output_format == "map":
            return generate_map_response(results, map_points, file.filename, conversion_direction)
        else:
            return generate_csv_response(results, df, file.filename, conversion_direction)
        
    except Exception as e:
        logger.error(f"Batch conversion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")

def detect_csv_columns(df):
    """Detect coordinate and format columns in CSV"""
    possible_lat_names = ['latitude', 'lat', 'y', 'northing', 'y_coordinate']
    possible_lon_names = ['longitude', 'lon', 'long', 'x', 'easting', 'x_coordinate']
    
    # Also include UTM-specific names
    possible_utm_easting = ['easting', 'x', 'x_coordinate', 'east', 'utm_easting']
    possible_utm_northing = ['northing', 'y', 'y_coordinate', 'north', 'utm_northing']
    
    lat_col = lon_col = lat_format_col = lon_format_col = None
    
    for col in df.columns:
        col_lower = col.lower().strip()
        
        # Check for geographic coordinates first
        if col_lower in possible_lat_names:
            lat_col = col
        elif col_lower in possible_lon_names:
            lon_col = col
        # Then check for UTM coordinates
        elif col_lower in possible_utm_easting and not lon_col:
            lon_col = col  # Easting goes to longitude column for processing
        elif col_lower in possible_utm_northing and not lat_col:
            lat_col = col  # Northing goes to latitude column for processing
        elif 'lat_format' in col_lower:
            lat_format_col = col
        elif 'lon_format' in col_lower or 'long_format' in col_lower:
            lon_format_col = col
        elif col_lower == 'format' and lat_format_col is None:
            lat_format_col = col
            lon_format_col = col
    
    # Default to decimal degrees if format not specified
    if not lat_format_col:
        lat_format_col = 'dd'
    if not lon_format_col:
        lon_format_col = 'dd'
    
    return lat_col, lon_col, lat_format_col, lon_format_col

def generate_csv_response(results, original_df, filename, conversion_direction):
    """Generate clean CSV download response with original columns + converted coordinates"""
    # Create a new DataFrame that maintains original structure
    output_data = []
    
    for result in results:
        # Start with original columns in their original order
        output_row = {}
        
        # Add all original columns (maintains original order)
        for col in original_df.columns:
            if col in result:
                output_row[col] = result[col]
        
        # Append converted coordinates based on conversion direction
        if result['status'] == 'success':
            if conversion_direction == "to_utm":
                # 4326 → 21037: Append X_21037, Y_21037
                output_row['X_21037'] = result['easting_21037']
                output_row['Y_21037'] = result['northing_21037']
            else:
                # 21037 → 4326: Append latitude_dd, longitude_dd
                output_row['latitude_dd'] = result['latitude_dd']
                output_row['longitude_dd'] = result['longitude_dd']
        else:
            # For failed conversions, add empty converted columns
            if conversion_direction == "to_utm":
                output_row['X_21037'] = None
                output_row['Y_21037'] = None
            else:
                output_row['latitude_dd'] = None
                output_row['longitude_dd'] = None
        
        output_data.append(output_row)
    
    output_df = pd.DataFrame(output_data)
    
    # Ensure column order: original columns first, then converted coordinates
    original_columns = list(original_df.columns)
    if conversion_direction == "to_utm":
        final_columns = original_columns + ['X_21037', 'Y_21037']
    else:
        final_columns = original_columns + ['latitude_dd', 'longitude_dd']
    
    # Reorder columns to maintain original order + appended converted coordinates
    output_df = output_df.reindex(columns=final_columns)
    
    output_io = io.StringIO()
    output_df.to_csv(output_io, index=False)
    output_bytes = output_io.getvalue().encode('utf-8-sig')
    
    return Response(
        content=output_bytes,
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="converted_{filename}"'}
    )

def generate_map_response(results, map_points, filename, conversion_direction):
    """Generate HTML map visualization response with efficiency safeguards"""
    
    # EFFICIENCY: Limit map points for very large datasets
    MAX_MAP_POINTS = 500  # Prevent browser overload
    if len(map_points) > MAX_MAP_POINTS:
        map_points = map_points[:MAX_MAP_POINTS]
        logger.warning(f"Large dataset: Limited to {MAX_MAP_POINTS} points for map display")
    
    # Calculate center point
    if map_points:
        center_lat = sum(point['lat'] for point in map_points) / len(map_points)
        center_lon = sum(point['lon'] for point in map_points) / len(map_points)
    else:
        center_lat, center_lon = -1.2833, 36.8167
    
    # EFFICIENCY: Limit results data sent to frontend
    simplified_results = []
    for result in results[:MAX_MAP_POINTS]:  # Only send what's needed for display
        simplified_result = {
            'original_row': result['original_row'],
            'status': result['status']
        }
        # Only include non-coordinate attributes
        for key, value in result.items():
            if key not in ['input_latitude', 'input_longitude', 'latitude_dd', 
                          'longitude_dd', 'easting_21037', 'northing_21037',
                          'input_easting', 'input_northing', 'latitude_dms', 'longitude_dms']:
                if value and str(value) != 'nan':
                    simplified_result[key] = value
        simplified_results.append(simplified_result)
    
    map_points_json = json.dumps(map_points)
    results_json = json.dumps(simplified_results)
    
    # Add efficiency warning for large datasets
    efficiency_note = ""
    if len(results) > MAX_MAP_POINTS:
        efficiency_note = f"""
        <div class="alert alert-warning mt-3">
            <strong>Note:</strong> Large dataset detected. Showing first {MAX_MAP_POINTS} points on map. 
            Download CSV for complete results.
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Batch Conversion Results - Map View</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body {{ background-color: #f8f9fa; }}
            .card {{ box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); }}
            #map {{ height: 500px; border-radius: 0.375rem; }}
            .results-table {{ max-height: 400px; overflow-y: auto; }}
            .success-badge {{ background-color: #28a745; }}
            .error-badge {{ background-color: #dc3545; }}
            .skipped-badge {{ background-color: #6c757d; }}
            .popup-content {{ max-width: 300px; max-height: 400px; overflow-y: auto; }}
            .popup-section {{ margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #eee; }}
            .popup-section:last-child {{ border-bottom: none; }}
            .coordinates-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }}
            .coord-label {{ font-weight: bold; color: #555; font-size: 0.9em; }}
            .coord-value {{ font-family: monospace; font-size: 0.9em; }}
            .efficient-marker {{ cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="container mt-4">
            <div class="row">
                <div class="col-md-12">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h1>Batch Conversion Results</h1>
                        <div>
                            <a href="/" class="btn btn-success me-2">New Conversion</a>
                            <a href="/" class="btn btn-outline-primary">← Back to Converter</a>
                        </div>
                    </div>
                    
                    {efficiency_note}
                    
                    <div class="card mb-4">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h5 class="mb-0">📍 Map Visualization ({len(map_points)} points)</h5>
                            <small class="text-muted">Click markers for details</small>
                        </div>
                        <div class="card-body">
                            <div id="map"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">📊 Conversion Summary ({len(results)} records)</h5>
                        </div>
                        <div class="card-body">
                            <div class="results-table">
                                <table class="table table-striped table-sm">
                                    <thead>
                                        <tr>
                                            <th>Row</th>
                                            <th>Name/ID</th>
                                            <th>Original Coordinates</th>
                                            <th>Converted Coordinates</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
    """
    
    for result in results:
        status_class = "success-badge" if result['status'] == 'success' else "error-badge"
        if 'skipped' in result['status']:
            status_class = "skipped-badge"
        
        # Try to get a name for display
        name_display = f"Row {result['original_row']}"
        for name_col in ['name', 'id', 'description', 'site_name', 'location']:
            if name_col in result and result[name_col] and str(result[name_col]) != 'nan':
                name_display = str(result[name_col])
                break
        
        # Display appropriate coordinates based on conversion direction
        if conversion_direction == "to_utm":
            original_coords = f"{result.get('input_latitude', 'N/A')}, {result.get('input_longitude', 'N/A')}"
            if result['status'] == 'success':
                converted_coords = f"{result.get('easting_21037', 'N/A')}, {result.get('northing_21037', 'N/A')}"
            else:
                converted_coords = "N/A"
        else:
            original_coords = f"{result.get('input_easting', 'N/A')}, {result.get('input_northing', 'N/A')}"
            if result['status'] == 'success':
                converted_coords = f"{result.get('latitude_dd', 'N/A')}, {result.get('longitude_dd', 'N/A')}"
            else:
                converted_coords = "N/A"
        
        html_content += f"""
                                        <tr>
                                            <td>{result['original_row']}</td>
                                            <td>{name_display}</td>
                                            <td>{original_coords}</td>
                                            <td>{converted_coords}</td>
                                            <td><span class="badge {status_class}">{result['status']}</span></td>
                                        </tr>
        """
    
    html_content += f"""
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // CRITICAL FIX: Wait for DOM to be fully loaded
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('Initializing map...');
                
                // Initialize map
                const map = L.map('map', {{
                    preferCanvas: true
                }}).setView([{center_lat}, {center_lon}], 8);
                
                // Add tile layer
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }}).addTo(map);

                const allResults = {results_json};
                const points = {map_points_json};
                const markers = [];
                
                console.log('Processing', points.length, 'points');
                
                // Add points to map
                points.forEach((point) => {{
                    const marker = L.marker([point.lat, point.lon]).addTo(map);
                    markers.push(marker);
                    
                    const resultData = allResults.find(r => r.original_row === point.row_number);
                    
                    // Build popup content
                    let popupContent = `
                        <div class="popup-content">
                            <h6 style="margin-bottom: 12px; color: #2c3e50;">${{point.name}}</h6>
                    `;
                    
                    // Coordinates Section
                    if (resultData && resultData.status === 'success') {{
                        popupContent += `
                            <div class="popup-section">
                                <strong style="color: #e74c3c; margin-bottom: 8px; display: block;">📍 Coordinates</strong>
                                <div class="coordinates-grid">
                                    <div class="coord-label">WGS84:</div>
                                    <div class="coord-value">${{point.lat.toFixed(6)}}°, ${{point.lon.toFixed(6)}}°</div>
                        `;
                        
                        if (point.conversion_type === 'to_utm') {{
                            popupContent += `
                                    <div class="coord-label">UTM Easting:</div>
                                    <div class="coord-value">${{point.easting || 'N/A'}}</div>
                                    
                                    <div class="coord-label">UTM Northing:</div>
                                    <div class="coord-value">${{point.northing || 'N/A'}}</div>
                            `;
                        }}
                        
                        popupContent += `
                                </div>
                            </div>
                        `;
                    }} else {{
                        popupContent += `
                            <div class="popup-section">
                                <strong style="color: #e74c3c; margin-bottom: 8px; display: block;">📍 Coordinates</strong>
                                <div style="color: #dc3545; font-style: italic;">Conversion failed</div>
                            </div>
                        `;
                    }}
                    
                    // Add all other CSV attributes
                    if (resultData) {{
                        let additionalAttributes = '';
                        let hasAdditionalData = false;
                        
                        for (const [key, value] of Object.entries(resultData)) {{
                            const excludedFields = [
                                'original_row', 'input_latitude', 'input_longitude', 
                                'latitude_dd', 'longitude_dd', 'easting_21037', 
                                'northing_21037', 'status', 'lat_format', 'lon_format',
                                'input_easting', 'input_northing', 'latitude_dms', 'longitude_dms'
                            ];
                            
                            if (!excludedFields.includes(key) && 
                                value !== null && 
                                value !== undefined && 
                                value !== 'nan' && 
                                value !== 'NaN' &&
                                String(value).trim() !== '') {{
                                
                                const displayKey = key.replace(/_/g, ' ')
                                                    .replace(/\\b\\w/g, l => l.toUpperCase());
                                
                                additionalAttributes += `
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                        <span class="coord-label">${{displayKey}}:</span>
                                        <span class="coord-value">${{value}}</span>
                                    </div>
                                `;
                                hasAdditionalData = true;
                            }}
                        }}
                        
                        if (hasAdditionalData) {{
                            popupContent += `
                                <div class="popup-section">
                                    <strong style="color: #3498db; margin-bottom: 8px; display: block;">📋 Attributes</strong>
                                    ${{additionalAttributes}}
                                </div>
                            `;
                        }}
                    }}
                    
                    popupContent += `
                            <div class="popup-section" style="text-align: center; margin-top: 10px;">
                                <small style="color: #7f8c8d;"><em>Row ${{point.row_number}}</em></small>
                            </div>
                        </div>
                    `;
                    
                    marker.bindPopup(popupContent);
                }});

                // Fit map to show all points
                if (markers.length > 0) {{
                    console.log('Fitting map bounds to', markers.length, 'markers');
                    const group = new L.featureGroup(markers);
                    map.fitBounds(group.getBounds().pad(0.1));
                }} else {{
                    console.log('No markers to display');
                }}
                
                console.log('Map initialization complete');
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Coordinate Converter"}

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.post("/test/upload")
async def test_upload(file: UploadFile = File(...)):
    """Test endpoint to check file upload functionality"""
    try:
        contents = await file.read()
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": len(contents),
            "first_100_chars": contents.decode('utf-8')[:100]
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/test/simple-batch")
async def test_simple_batch():
    """Simple test without file upload"""
    try:
        # Test data
        test_data = """latitude,longitude,lat_format,lon_format
-1.2833,36.8167,dd,dd"""
        
        df = pd.read_csv(io.StringIO(test_data))
        logger.info(f"Test DataFrame: {df}")
        
        row = df.iloc[0]
        lat_dd = converter.parse_dms_to_decimal(str(row['latitude']), str(row['lat_format']))
        lon_dd = converter.parse_dms_to_decimal(str(row['longitude']), str(row['lon_format']))
        easting, northing = converter.transform_4326_to_21037(lat_dd, lon_dd)
        
        return {
            "status": "success",
            "result": {
                "input": {"lat": row['latitude'], "lon": row['longitude']},
                "output": {"easting": easting, "northing": northing}
            }
        }
    except Exception as e:
        logger.error(f"Simple test failed: {str(e)}")
        return {"status": "error", "detail": str(e)}

@app.get("/download-sample-csv")
async def download_sample_csv():
    """Generate and download flexible sample CSV"""
    sample_data = """name,latitude,longitude,description,site_id
Nairobi Head Office,-1.2833,36.8167,Main headquarters,001
Field Site A,1°17'00"S,36°49'00"E,Research station,002
Mombasa Branch,-4.0500,39.6667,Coastal office,003
Kampala Reference,0.3167,32.5833,Regional reference,004"""
    
    return Response(
        content=sample_data.encode('utf-8-sig'),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=flexible_sample_coordinates.csv"}
    )