// Initialize Leaflet map
let map = L.map('map').setView([-1.2833, 36.8167], 6); // Center on Kenya

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Variables to store markers
let inputMarker = null;
let outputMarker = null;

// Add click event to map
map.on('click', function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    // Update coordinate inputs
    document.getElementById('latitude').value = lat.toFixed(6);
    document.getElementById('longitude').value = lng.toFixed(6);
    document.getElementById('latFormat').value = 'dd';
    document.getElementById('lonFormat').value = 'dd';
    
    // Add marker to map
    if (inputMarker) {
        map.removeLayer(inputMarker);
    }
    inputMarker = L.marker([lat, lng]).addTo(map)
        .bindPopup(`Clicked: ${lat.toFixed(6)}, ${lng.toFixed(6)}`)
        .openPopup();
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
            headers: {
                'Content-Type': 'application/json',
            },
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
            headers: {
                'Content-Type': 'application/json',
            },
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
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    try {
        const response = await fetch('/convert/batch', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Create download link for the result
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'converted_coordinates.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            alert('Conversion completed! File downloaded.');
        } else {
            const error = await response.json();
            alert('Error: ' + error.detail);
        }
    } catch (error) {
        alert('Network error: ' + error.message);
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
    
    // Center map on the point
    map.setView([latNum, lngNum], 10);
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
    
    // Center map on the point
    map.setView([lat, lng], 10);
}

// Add scale control
L.control.scale().addTo(map);

// Add sample coordinates for quick testing
function addSampleCoordinates() {
    const samples = [
        { lat: "-1.2833", lon: "36.8167", latFormat: "dd", lonFormat: "dd", desc: "Nairobi Approx" },
        { lat: "1°17'00\"S", lon: "36°49'00\"E", latFormat: "dms", lonFormat: "dms", desc: "Nairobi DMS" },
        { lat: "4°03.0'S", lon: "39°40.0'E", latFormat: "dm", lonFormat: "dm", desc: "Mombasa" }
    ];
    
    const sampleContainer = document.createElement('div');
    sampleContainer.className = 'mt-3';
    sampleContainer.innerHTML = '<h6>Quick Test Samples:</h6>';
    
    samples.forEach(sample => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-secondary btn-sm me-2 mb-2';
        btn.textContent = sample.desc;
        btn.onclick = () => {
            document.getElementById('latitude').value = sample.lat;
            document.getElementById('longitude').value = sample.lon;
            document.getElementById('latFormat').value = sample.latFormat;
            document.getElementById('lonFormat').value = sample.lonFormat;
        };
        sampleContainer.appendChild(btn);
    });
    
    document.getElementById('singleForm').appendChild(sampleContainer);
}

// Initialize sample coordinates when page loads
document.addEventListener('DOMContentLoaded', addSampleCoordinates);