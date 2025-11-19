from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import json
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
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
async def convert_batch(file: UploadFile = File(...)):
    """Convert batch of coordinates from CSV - WITH ENHANCED INPUT CLEANING"""
    logger.info(f"Batch conversion started for file: {file.filename}")
    
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
        logger.info(f"DataFrame created with columns: {df.columns.tolist()}")
        
        # Validate required columns
        required_cols = ['latitude', 'longitude', 'lat_format', 'lon_format']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            error_msg = f"Missing required columns: {missing_cols}. CSV must contain: {required_cols}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Process each row
        results = []
        for index, row in df.iterrows():
            try:
                # Get and clean the input coordinates
                lat_input = str(row['latitude'])
                lon_input = str(row['longitude'])
                
                # Apply the same cleaning to individual fields
                for wrong, correct in cleaning_replacements:
                    lat_input = lat_input.replace(wrong, correct)
                    lon_input = lon_input.replace(wrong, correct)
                
                lat_format = str(row['lat_format']).strip()
                lon_format = str(row['lon_format']).strip()
                
                # Parse coordinates
                lat_dd = converter.parse_dms_to_decimal(lat_input, lat_format)
                lon_dd = converter.parse_dms_to_decimal(lon_input, lon_format)
                
                # Transform coordinates
                easting, northing = converter.transform_4326_to_21037(lat_dd, lon_dd)
                
                results.append({
                    'input_latitude': lat_input,  # Use cleaned version
                    'input_longitude': lon_input, # Use cleaned version
                    'easting': round(easting, 3),
                    'northing': round(northing, 3),
                    'status': 'success'
                })
                
            except Exception as e:
                error_msg = f"error: {str(e)}"
                results.append({
                    'input_latitude': str(row['latitude']),
                    'input_longitude': str(row['longitude']),
                    'easting': None,
                    'northing': None,
                    'status': error_msg
                })
        
        # Create output with explicit UTF-8 encoding
        output_df = pd.DataFrame(results)
        output_io = io.StringIO()
        output_df.to_csv(output_io, index=False)
        output_bytes = output_io.getvalue().encode('utf-8-sig')  # Use utf-8-sig for Excel compatibility
        
        successful_count = len([r for r in results if r['status'] == 'success'])
        logger.info(f"Batch conversion completed. Successful: {successful_count}/{len(results)}")
        
        return Response(
            content=output_bytes,
            media_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="converted_{file.filename}"'}
        )
        
    except Exception as e:
        logger.error(f"Batch conversion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
    """Generate and download sample CSV with proper encoding"""
    sample_data = """latitude,longitude,lat_format,lon_format
-1.2833,36.8167,dd,dd
1°17'00"S,36°49'00"E,dms,dms
1°17.0'S,36°49.0'E,dm,dm
-4.0500,39.6667,dd,dd
0.3167,32.5833,dd,dd"""
    
    # Use utf-8-sig for Excel compatibility (adds BOM)
    return Response(
        content=sample_data.encode('utf-8-sig'),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=sample_coordinates.csv"}
    )