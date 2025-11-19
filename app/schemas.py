from pydantic import BaseModel
from typing import Optional, Literal

class ConversionRequest(BaseModel):
    latitude: str
    longitude: str
    lat_format: Literal["dd", "dm", "dms"]
    lon_format: Literal["dd", "dm", "dms"]

class ReverseConversionRequest(BaseModel):
    easting: float
    northing: float

class PointResponse(BaseModel):
    easting: float
    northing: float
    input_lat: str
    input_lon: str

class ReversePointResponse(BaseModel):
    latitude: float
    longitude: float
    latitude_dms: str
    longitude_dms: str
    input_easting: float
    input_northing: float

class BatchResponse(BaseModel):
    filename: str
    record_count: int
    success_count: int