import logging
import sys
from datetime import datetime
import json

def setup_logging():
    """Setup comprehensive logging for audit purposes"""
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/converter_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

# Global logger instance
logger = setup_logging()

def log_conversion(original_coords, converted_coords, conversion_type, user_agent="Unknown"):
    """Log conversion activities for audit trail"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "conversion_type": conversion_type,
        "original_coordinates": original_coords,
        "converted_coordinates": converted_coords,
        "user_agent": user_agent
    }
    
    logger.info(f"Conversion performed: {json.dumps(log_entry)}")