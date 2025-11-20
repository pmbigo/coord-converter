// Initialize Leaflet map with performance options
let map = L.map('map', {
    preferCanvas: true  // Better performance for many markers
}).setView([-1.2833, 36.8167], 6); // Center on Kenya

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
}).addTo(map);

// Variables to store markers
let inputMarker = null;
let outputMarker = null;

// Add scale control
L.control.scale({imperial: false}).addTo(map);

// Map click event
map.on('click', function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    // Update coordinate inputs
    document.getElementById('latitude').value = lat.toFixed(6);
    document.getElementById('longitude').value = lng.toFixed(6);
    document.getElementById('latFormat').value = 'dd';
    document.getElementById('lonFormat').value = 'dd';
    
    // Clear existing markers
    if (inputMarker) {
        map.removeLayer(inputMarker);
    }
    if (outputMarker) {
        map.removeLayer(outputMarker);
    }
    
    // Add new marker at clicked location
    inputMarker = L.marker([lat, lng]).addTo(map)
        .bindPopup(`Clicked: ${lat.toFixed(6)}, ${lng.toFixed(6)}`)
        .openPopup();
    
    // Center map on clicked location
    map.setView([lat, lng], 15, {
        animate: true,
        duration: 1
    });
});

// Single coordinate conversion
document.getElementById('singleForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        latitude: document.getElementById('latitude').value,
        longitude: document.getElementById('longitude').value,
        lat_format: document.getElementById('latFormat').value,
        lon_format: document.getElementById('lonFormat').value
    };
    
    try {
        const response = await fetch('/convert/point', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            const result = await response.json();
            document.getElementById('resultEasting').textContent = result.easting;
            document.getElementById('resultNorthing').textContent = result.northing;
            document.getElementById('singleResult').style.display = 'block';
            
            // Update map with converted point
            updateMapWithResult(formData.latitude, formData.longitude, result.easting, result.northing);
        } else {
            const error = await response.json();
            alert('Error: ' + error.detail);
        }
    } catch (error) {
        alert('Network error: ' + error.message);
    }
});

// Reverse conversion
document.getElementById('reverseForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        easting: parseFloat(document.getElementById('easting').value),
        northing: parseFloat(document.getElementById('northing').value)
    };
    
    try {
        const response = await fetch('/convert/reverse', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            const result = await response.json();
            document.getElementById('resultLatitude').textContent = result.latitude;
            document.getElementById('resultLongitude').textContent = result.longitude;
            document.getElementById('resultDMS').textContent = `${result.latitude_dms}, ${result.longitude_dms}`;
            document.getElementById('reverseResult').style.display = 'block';
            
            // Update map with reverse converted point
            updateMapWithReverseResult(result.latitude, result.longitude, formData.easting, formData.northing);
        } else {
            const error = await response.json();
            alert('Error: ' + error.detail);
        }
    } catch (error) {
        alert('Network error: ' + error.message);
    }
});

// Batch conversion
document.getElementById('batchForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('csvFile');
    const showMap = document.getElementById('showMap').checked;
    const conversionDirection = document.getElementById('conversionDirection').value;
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('output_format', showMap ? 'map' : 'csv');
    formData.append('conversion_direction', conversionDirection);
    
    // Show loading state
    const batchButton = document.querySelector('#batchForm button[type="submit"]');
    const originalText = batchButton.innerHTML;
    batchButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    batchButton.disabled = true;
    
    try {
        const response = await fetch('/convert/batch', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            if (showMap) {
                // For map view, replace the current page with results
                const html = await response.text();
                document.open();
                document.write(html);
                document.close();
            } else {
                // For CSV download, keep existing behavior
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'converted_coordinates.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                alert('Conversion completed! File downloaded.');
            }
        } else {
            const error = await response.json();
            alert('Error: ' + error.detail);
        }
    } catch (error) {
        alert('Network error: ' + error.message);
    } finally {
        // Restore button state
        batchButton.innerHTML = originalText;
        batchButton.disabled = false;
    }
});

// Map update functions
function updateMapWithResult(lat, lng, easting, northing) {
    // Parse coordinates to numbers
    const latNum = parseFloat(lat);
    const lngNum = parseFloat(lng);
    
    // Clear previous markers
    if (inputMarker) {
        map.removeLayer(inputMarker);
    }
    if (outputMarker) {
        map.removeLayer(outputMarker);
    }
    
    // Add input marker (blue)
    inputMarker = L.marker([latNum, lngNum])
        .addTo(map)
        .bindPopup(`
            <strong>Input (WGS84):</strong><br>
            Lat: ${lat}<br>
            Lon: ${lng}<br>
            <strong>Output (UTM 37S):</strong><br>
            Easting: ${easting}<br>
            Northing: ${northing}
        `)
        .openPopup();
    
    // Center and zoom map on the point with proper animation
    map.setView([latNum, lngNum], 15, {
        animate: true,
        duration: 1
    });
}

function updateMapWithReverseResult(lat, lng, easting, northing) {
    // Clear previous markers
    if (inputMarker) {
        map.removeLayer(inputMarker);
    }
    if (outputMarker) {
        map.removeLayer(outputMarker);
    }
    
    // Add output marker (green)
    outputMarker = L.marker([lat, lng])
        .addTo(map)
        .bindPopup(`
            <strong>Input (UTM 37S):</strong><br>
            Easting: ${easting}<br>
            Northing: ${northing}<br>
            <strong>Output (WGS84):</strong><br>
            Lat: ${lat.toFixed(6)}°<br>
            Lon: ${lng.toFixed(6)}°
        `)
        .openPopup();
    
    // Center and zoom map on the point with proper animation
    map.setView([lat, lng], 15, {
        animate: true,
        duration: 1
    });
}

// Sample coordinates function
function setSample(location) {
    const samples = {
        nairobi: { lat: "-1.2833", lon: "36.8167", latFormat: "dd", lonFormat: "dd" },
        mombasa: { lat: "-4.0500", lon: "39.6667", latFormat: "dd", lonFormat: "dd" },
        kampala: { lat: "0.3167", lon: "32.5833", latFormat: "dd", lonFormat: "dd" }
    };
    
    const sample = samples[location];
    if (sample) {
        document.getElementById('latitude').value = sample.lat;
        document.getElementById('longitude').value = sample.lon;
        document.getElementById('latFormat').value = sample.latFormat;
        document.getElementById('lonFormat').value = sample.lonFormat;
    }
}

// Update batch button text based on selection
document.getElementById('showMap').addEventListener('change', function(e) {
    const batchButtonText = document.getElementById('batchButtonText');
    if (e.target.checked) {
        batchButtonText.textContent = 'Convert and Show on Map';
    } else {
        batchButtonText.textContent = 'Convert Batch File';
    }
});