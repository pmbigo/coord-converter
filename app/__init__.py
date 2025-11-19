"""
Coordinate Converter Package
Survey-grade GIS coordinate conversion tool
"""

__version__ = "2.0.0"
__author__ = "Coordinate Converter Team"

# Import key components to make them easily accessible
from .main import app
from .converters import CoordinateConverter
from .logger import setup_logging

# Initialize logging when package is imported
setup_logging()