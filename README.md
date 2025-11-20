# Coordinate Converter

A professional web application for converting coordinates between WGS84 (EPSG:4326) and UTM Zone 37S (EPSG:21037).

![Coordinate Converter](https://img.shields.io/badge/Version-2.1.0-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-orange)

## 🌟 Features

### 🔄 Coordinate Conversion
- **Single Point Conversion**: Convert individual coordinates between formats
- **Batch Processing**: Upload CSV files for bulk conversion
- **Multiple Input Formats**: 
  - Decimal Degrees (DD) - `-1.2833, 36.8167`
  - Degrees Minutes (DM) - `1°17.0'S, 36°49.0'E`  
  - Degrees Minutes Seconds (DMS) - `1°17'00"S, 36°49'00"E`
- **Bidirectional Conversion**: 4326 ↔ 21037

### 📊 Batch Processing
- **Flexible CSV Input**: Automatic column detection for coordinates
- **Multiple Output Options**:
  - CSV Download: Complete results with all original data
  - Interactive Map: Visualize all points with detailed popups
- **Efficiency Optimized**: Handles large datasets with performance safeguards

### 🗺️ Map Visualization
- **Interactive Maps**: Click to set coordinates or view results
- **Rich Popups**: Show original coordinates, converted values, and all CSV attributes
- **Auto-centering**: Maps automatically focus on your data
- **Performance Optimized**: Canvas-based rendering for smooth interaction

### 🎯 Survey Grade Accuracy
- **PROJ Library**: Industry-standard coordinate transformations
- **Millimeter Precision**: Geodetic datum transformations
- **Validation**: Comprehensive coordinate validation and error handling

## 🚀 Quick Start

### Live Demo
Visit the live application: [https://coord-converter.up.railway.app](https://coord-converter.up.railway.app)

### Single Coordinate Conversion
1. Enter coordinates in any format (DD, DM, DMS)
2. Select the appropriate format for each coordinate
3. Click "Convert to UTM" or use reverse conversion
4. View results on the interactive map

### Batch CSV Conversion
1. **Download Sample CSV** to see the format
2. **Prepare your CSV** with coordinate columns (flexible naming supported)
3. **Upload your file** and choose output format:
   - **CSV Download**: Get complete results as downloadable file
   - **Map Visualization**: See all points on an interactive map
4. **View Results**: Download CSV or explore on map with detailed popups

## 📁 CSV Format

### Supported Column Names
| Coordinate | Accepted Column Names |
|------------|----------------------|
| Latitude | `latitude`, `lat`, `y`, `northing`, `y_coordinate` |
| Longitude | `longitude`, `lon`, `long`, `x`, `easting`, `x_coordinate` |
| Format | `lat_format`, `lon_format`, `format` (optional, defaults to decimal) |

### Example CSV
```csv
name,latitude,longitude,description,site_id,elevation
Nairobi Office,-1.2833,36.8167,Main Headquarters,001,1700
Field Site A,1°17'00"S,36°49'00"E,Research Station,002,1200
Mombasa Branch,-4.0500,39.6667,Coastal Office,003,50

🛠️ Installation & Development
Prerequisites
Python 3.11+
Git

Local Development
# Clone repository
git clone https://github.com/pmbigo/coord-converter.git
cd coord-converter

# Create virtual environment
python -m venv coord_env
source coord_env/bin/activate  # Linux/Mac
# OR
coord_env\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Visit: http://localhost:8000

Deployment
The app is configured for easy deployment on Railway:

Push to GitHub

Connect repository to Railway

Automatic deployment with zero configuration

🏗️ Architecture
Backend
FastAPI: Modern, fast web framework

PyProj: Professional coordinate transformations

Pandas: Efficient CSV processing

Shapely: Geometric validation

Frontend
Bootstrap 5: Responsive UI components

Leaflet: Interactive maps

Vanilla JavaScript: Lightweight, no framework dependencies

Deployment
Railway: Serverless deployment platform

Docker: Containerized environment

Automatic HTTPS: Secure connections

📊 Performance
Single Conversions: Instant response

Batch Processing: Optimized for datasets up to 10,000 points

Map Visualization: Performance-optimized for 500+ points

Memory Efficient: Streaming processing for large files

🐛 Troubleshooting
Common Issues
CSV Upload Fails: Check column names match supported formats

Map Not Loading: Ensure JavaScript is enabled

Large Files Slow: Use CSV download option for datasets > 500 points

Getting Help
Check the sample CSV format

Test with single coordinates first

Use the health endpoint: /health

📄 License
MIT License - feel free to use in your projects.

🤝 Contributing
Contributions welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.
Disclaimer: Proficiency - Learner
