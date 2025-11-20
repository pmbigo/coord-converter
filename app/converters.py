from pyproj import Transformer
import re
from shapely.geometry import Point
from shapely.validation import explain_validity
import logging

logger = logging.getLogger(__name__)

class CoordinateConverter:
    def __init__(self):
        # EPSG:4326 (WGS84) to EPSG:21037 (UTM Zone 37S) and reverse
        self.transformer_forward = Transformer.from_crs("EPSG:4326", "EPSG:21037", always_xy=True)
        self.transformer_reverse = Transformer.from_crs("EPSG:21037", "EPSG:4326", always_xy=True)
    
    def validate_geometry(self, lat: float, lon: float) -> bool:
        """Validate coordinates using Shapely geometry library"""
        try:
            point = Point(lon, lat)
            validity = explain_validity(point)
            
            if validity != "Valid Geometry":
                logger.warning(f"Invalid geometry: {validity} for coordinates ({lat}, {lon})")
                return False
            
            # Additional validation for coordinate ranges
            if not (-90 <= lat <= 90):
                raise ValueError("Latitude must be between -90 and 90 degrees")
            if not (-180 <= lon <= 180):
                raise ValueError("Longitude must be between -180 and 180 degrees")
                
            return True
            
        except Exception as e:
            logger.error(f"Geometry validation failed: {str(e)}")
            raise ValueError(f"Coordinate validation failed: {str(e)}")
    
    def parse_dms_to_decimal(self, coord: str, format_type: str) -> float:
        """Parse coordinate from DMS, DM, or DD format to decimal degrees"""
        try:
            coord = coord.replace('d', '°').strip()
            
            if format_type == "dd":
                return float(coord)
            
            elif format_type == "dm":
                # Degrees and decimal minutes: 45°30.5'N or 45 30.5 N
                pattern = r'^(-?\d{1,3})[°\s]*\s*(\d+\.?\d*)\'?[\s]*([NSEW]?)$'
                match = re.match(pattern, coord.upper())
                if match:
                    degrees = float(match.group(1))
                    minutes = float(match.group(2))
                    direction = match.group(3)
                    
                    decimal = abs(degrees) + (minutes / 60)
                    if degrees < 0 or direction in ['S', 'W']:
                        decimal = -decimal
                    return decimal
            
            elif format_type == "dms":
                # Degrees, minutes, seconds: 45°30'30"N or 45 30 30 N
                pattern = r'^(-?\d{1,3})[°\s]*\s*(\d{1,2})\'?[\s]*\s*(\d+\.?\d*)"?[\s]*([NSEW]?)$'
                match = re.match(pattern, coord.upper())
                if match:
                    degrees = float(match.group(1))
                    minutes = float(match.group(2))
                    seconds = float(match.group(3))
                    direction = match.group(4)
                    
                    decimal = abs(degrees) + (minutes / 60) + (seconds / 3600)
                    if degrees < 0 or direction in ['S', 'W']:
                        decimal = -decimal
                    return decimal
            
            raise ValueError(f"Could not parse coordinate: '{coord}' in format {format_type}")
            
        except Exception as e:
            logger.error(f"Coordinate parsing failed: {str(e)}")
            raise ValueError(f"Invalid coordinate format: {str(e)}")
    
    def decimal_to_dms(self, decimal: float, coord_type: str) -> str:
        """Convert decimal degrees to DMS format"""
        try:
            # Determine if it's latitude or longitude
            if coord_type == "lat":
                direction = "N" if decimal >= 0 else "S"
            else:  # lon
                direction = "E" if decimal >= 0 else "W"
            
            decimal = abs(decimal)
            degrees = int(decimal)
            minutes_decimal = (decimal - degrees) * 60
            minutes = int(minutes_decimal)
            seconds = (minutes_decimal - minutes) * 60
            
            return f"{degrees}°{minutes:02d}'{seconds:06.3f}\"{direction}"
        except Exception as e:
            logger.error(f"DMS conversion failed: {str(e)}")
            raise ValueError(f"Could not convert to DMS: {str(e)}")
    
    def transform_4326_to_21037(self, lat: float, lon: float) -> tuple:
        """Transform WGS84 to UTM Zone 37S"""
        try:
            # Validate coordinates
            self.validate_geometry(lat, lon)
            
            # Check if coordinates are within reasonable bounds for Kenya/UTM 37S
            if lon < 30 or lon > 42:
                logger.warning(f"Longitude {lon} may be outside optimal range for UTM Zone 37S")
            
            easting, northing = self.transformer_forward.transform(lon, lat)
            logger.info(f"Transformed 4326->21037: ({lat}, {lon}) -> ({easting:.3f}, {northing:.3f})")
            return easting, northing
            
        except Exception as e:
            logger.error(f"Forward transformation failed: {str(e)}")
            raise ValueError(f"Transformation failed: {str(e)}")
    
    def transform_21037_to_4326(self, easting: float, northing: float) -> tuple:
        """Transform UTM Zone 37S to WGS84"""
        try:
            # Validate UTM coordinates (approximate ranges for Kenya)
            if not (0 <= easting <= 1000000):
                raise ValueError("Easting should be between -67,300 and 822,500")
            if not (0 <= northing <= 10000000):
                raise ValueError("Northing should be between 0 and 10,560,000")
            
            lon, lat = self.transformer_reverse.transform(easting, northing)
            
            # Validate the resulting coordinates
            self.validate_geometry(lat, lon)
            
            logger.info(f"Transformed 21037->4326: ({easting}, {northing}) -> ({lat:.6f}, {lon:.6f})")
            return lat, lon
            
        except Exception as e:
            logger.error(f"Reverse transformation failed: {str(e)}")
            raise ValueError(f"Reverse transformation failed: {str(e)}")