#!/usr/bin/env python3
"""
Drone Image/Video Viewer - Render.com Deployment
Supports GPS-tagged images and DJI SRT video files
"""
import os
import re
import html
import logging
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB limit for Render

# Upload folder - Render uses ephemeral storage, files reset on deploy
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'images'), exist_ok=True)

def parse_srt(srt_path):
    """Parse DJI SRT files with GPS data."""
    gps_data = []
    if not os.path.exists(srt_path):
        return gps_data
    
    with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [l.rstrip('\n') for l in f]
    
    for i, line in enumerate(lines):
        if '-->' in line:
            ts = line.split()[0]
            lat, lon, alt = None, None, None
            
            # Scan next few lines for GPS data
            for j in range(i + 1, min(i + 8, len(lines))):
                curr_line = lines[j]
                
                # Remove HTML tags first
                clean = re.sub(r'<.*?>', '', curr_line)
                
                # Format: [latitude: X] [longitude: Y] [rel_alt: Z abs_alt: W]
                lat_m = re.search(r'\[?latitude:\s*([+-]?\d+\.?\d*)\]?', clean, re.IGNORECASE)
                lon_m = re.search(r'\[?longitude:\s*([+-]?\d+\.?\d*)\]?', clean, re.IGNORECASE)
                
                if lat_m and lon_m:
                    try:
                        lat = float(lat_m.group(1))
                        lon = float(lon_m.group(1))
                        
                        # Look for altitude (prefer abs_alt over rel_alt)
                        abs_m = re.search(r'abs[_\s-]?alt\s*[:=]\s*([+-]?\d+(?:\.\d+)?)', clean, re.IGNORECASE)
                        rel_m = re.search(r'rel[_\s-]?alt\s*[:=]\s*([+-]?\d+(?:\.\d+)?)', clean, re.IGNORECASE)
                        
                        if abs_m:
                            alt = float(abs_m.group(1))
                        elif rel_m:
                            alt = float(rel_m.group(1))
                        
                        gps_data.append({
                            'timestamp': ts,
                            'lat': lat,
                            'lon': lon,
                            'alt': alt if alt is not None else 0
                        })
                        break
                    except ValueError:
                        pass
    
    log.info(f"[SRT] Parsed {len(gps_data)} GPS points from {os.path.basename(srt_path)}")
    return gps_data

def extract_gps_from_image(filepath):
    """Extract GPS from image EXIF data."""
    try:
        import exifread
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        
        gps_lat = tags.get('GPS GPSLatitude')
        gps_lat_ref = tags.get('GPS GPSLatitudeRef')
        gps_lon = tags.get('GPS GPSLongitude')
        gps_lon_ref = tags.get('GPS GPSLongitudeRef')
        gps_alt = tags.get('GPS GPSAltitude')
        
        if not all([gps_lat, gps_lat_ref, gps_lon, gps_lon_ref]):
            return None
        
        def dms_to_decimal(dms, ref):
            degrees = float(dms.values[0].num) / float(dms.values[0].den)
            minutes = float(dms.values[1].num) / float(dms.values[1].den)
            seconds = float(dms.values[2].num) / float(dms.values[2].den)
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal
        
        lat = dms_to_decimal(gps_lat, str(gps_lat_ref))
        lon = dms_to_decimal(gps_lon, str(gps_lon_ref))
        
        alt = 0
        if gps_alt:
            try:
                alt = float(gps_alt.values[0].num) / float(gps_alt.values[0].den)
            except:
                pass
        
        return {'lat': lat, 'lon': lon, 'alt': alt}
    except Exception as e:
        log.debug(f"GPS extraction failed: {e}")
        return None

def create_map(images_data, video_gps_data):
    """Create Folium map with markers and tracks."""
    import folium
    from folium import plugins
    
    # Calculate center
    all_coords = []
    if images_data:
        all_coords.extend([(img['gps']['lat'], img['gps']['lon']) for img in images_data])
    if video_gps_data:
        all_coords.extend([(pt['lat'], pt['lon']) for pt in video_gps_data])
    
    if not all_coords:
        center = [43.65, -79.38]  # Default to Toronto
        zoom = 12
    else:
        center = [
            sum(c[0] for c in all_coords) / len(all_coords),
            sum(c[1] for c in all_coords) / len(all_coords)
        ]
        zoom = 15
    
    m = folium.Map(location=center, zoom_start=zoom, tiles='OpenStreetMap')
    
    # Image markers with track
    if images_data:
        img_fg = folium.FeatureGroup(name='Images', show=True)
        img_track_fg = folium.FeatureGroup(name='Image Track', show=True)
        img_coords = []
        
        for img in images_data:
            lat, lon = img['gps']['lat'], img['gps']['lon']
            img_coords.append([lat, lon])
            
            popup_html = f'''
            <div style="width:200px">
                <img src="/uploads/images/{img['filename']}" style="width:100%;cursor:pointer" 
                     onclick="parent.showImage('/uploads/images/{img['filename']}')" 
                     title="Click to view full image">
                <p style="margin:5px 0"><strong>{img['filename']}</strong></p>
                <button onclick="parent.showImage('/uploads/images/{img['filename']}')" 
                        style="width:100%;padding:5px;background:#1976d2;color:white;border:none;cursor:pointer;border-radius:3px">
                    Show image left
                </button>
            </div>
            '''
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=220),
                icon=folium.Icon(color='blue', icon='camera', prefix='fa'),
                tooltip=img['filename']
            ).add_to(img_fg)
        
        # Add blue polyline connecting images
        if len(img_coords) > 1:
            folium.PolyLine(
                img_coords,
                color='#1976d2',
                weight=3,
                opacity=0.7,
                tooltip='Image track'
            ).add_to(img_track_fg)
        
        img_fg.add_to(m)
        img_track_fg.add_to(m)
    
    # Video GPS track
    if video_gps_data:
        video_fg = folium.FeatureGroup(name='Video Points', show=True)
        track_fg = folium.FeatureGroup(name='Track', show=True)
        
        track_coords = [[pt['lat'], pt['lon']] for pt in video_gps_data]
        
        # Red polyline for video track
        folium.PolyLine(
            track_coords,
            color='red',
            weight=3,
            opacity=0.7,
            tooltip='Video flight path'
        ).add_to(track_fg)
        
        # Sample markers (every 30 points to avoid clutter)
        for i, pt in enumerate(video_gps_data):
            if i % 30 == 0:
                folium.CircleMarker(
                    location=[pt['lat'], pt['lon']],
                    radius=4,
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.6,
                    popup=f"Time: {pt['timestamp']}<br>Alt: {pt['alt']:.1f}m"
                ).add_to(video_fg)
        
        video_fg.add_to(m)
        track_fg.add_to(m)
    
    # Layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m.get_root().render()

@app.route('/')
def index():
    """Main page."""
    images_data = []
    video_gps_data = []
    video_file = None
    
    # Scan for uploaded images
    img_dir = os.path.join(UPLOAD_FOLDER, 'images')
    if os.path.exists(img_dir):
        for fname in os.listdir(img_dir):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                fpath = os.path.join(img_dir, fname)
                gps = extract_gps_from_image(fpath)
                if gps:
                    images_data.append({'filename': fname, 'gps': gps})
    
    # Scan for video and SRT
    for fname in os.listdir(UPLOAD_FOLDER):
        if fname.lower().endswith(('.mp4', '.mov', '.avi')):
            video_file = fname
        elif fname.lower().endswith('.srt'):
            srt_path = os.path.join(UPLOAD_FOLDER, fname)
            video_gps_data = parse_srt(srt_path)
    
    log.info(f"[INDEX] Images: {len(images_data)}, Video GPS: {len(video_gps_data)}")
    
    # Create map
    map_html = create_map(images_data, video_gps_data)
    
    # HTML template
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Drone Viewer - Render</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/viewerjs/1.11.6/viewer.min.css">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; display: flex; flex-direction: column; height: 100vh; }
            #header { background: #1976d2; color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
            #header h1 { font-size: 24px; }
            #upload-form { display: flex; gap: 10px; align-items: center; }
            #upload-form input[type="file"] { padding: 5px; }
            #upload-form button { background: white; color: #1976d2; border: none; padding: 8px 15px; cursor: pointer; border-radius: 4px; font-weight: bold; }
            #upload-form button:hover { background: #f0f0f0; }
            #clear-btn { background: #d32f2f; color: white; border: none; padding: 8px 15px; cursor: pointer; border-radius: 4px; font-weight: bold; }
            #clear-btn:hover { background: #b71c1c; }
            #content { display: flex; flex: 1; overflow: hidden; }
            #left-panel { width: 40%; background: #f5f5f5; display: flex; flex-direction: column; border-right: 2px solid #ccc; }
            #image-viewer { flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #333; }
            #image-viewer img { max-width: 100%; max-height: 100%; object-fit: contain; cursor: pointer; }
            #video-container { padding: 10px; background: #222; }
            #video-container video { width: 100%; max-height: 300px; }
            #right-panel { flex: 1; position: relative; }
            #map-frame { width: 100%; height: 100%; border: none; }
            .placeholder { color: #999; text-align: center; padding: 20px; }
        </style>
    </head>
    <body>
        <div id="header">
            <h1>🚁 Drone Viewer (Render.com)</h1>
            <form id="upload-form" method="POST" action="/upload" enctype="multipart/form-data">
                <input type="file" name="files" multiple accept="image/*,video/*,.srt" required>
                <button type="submit">Upload</button>
                <button type="button" id="clear-btn" onclick="clearAllData()">Clear All Data</button>
            </form>
        </div>
        <div id="content">
            <div id="left-panel">
                <div id="image-viewer">
                    <div class="placeholder">Upload images or click map markers to view</div>
                </div>
                {% if video_file %}
                <div id="video-container">
                    <video controls>
                        <source src="/uploads/{{ video_file }}" type="video/mp4">
                    </video>
                </div>
                {% endif %}
            </div>
            <div id="right-panel">
                <iframe id="map-frame" srcdoc="{{ map_html | safe }}"></iframe>
            </div>
        </div>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/viewerjs/1.11.6/viewer.min.js"></script>
        <script>
            let viewer = null;
            
            function showImage(imgPath) {
                const container = document.getElementById('image-viewer');
                container.innerHTML = '<img src="' + imgPath + '" id="main-image">';
                
                const img = document.getElementById('main-image');
                if (viewer) viewer.destroy();
                viewer = new Viewer(img, {
                    inline: false,
                    navbar: false,
                    toolbar: {
                        zoomIn: 1, zoomOut: 1, oneToOne: 1, reset: 1,
                        rotateLeft: 1, rotateRight: 1, flipHorizontal: 1, flipVertical: 1
                    }
                });
                viewer.show();
            }
            
            function clearAllData() {
                if (!confirm('This will delete all uploaded images and videos. Continue?')) return;
                fetch('/clear_data', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert(data.message || 'Data cleared');
                        window.location.reload();
                    })
                    .catch(e => alert('Error: ' + e));
            }
            
            window.showImage = showImage;
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html_template, map_html=map_html, video_file=video_file)

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file uploads."""
    files = request.files.getlist('files')
    
    for file in files:
        if file.filename:
            fname = file.filename
            
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                save_path = os.path.join(UPLOAD_FOLDER, 'images', fname)
            else:
                save_path = os.path.join(UPLOAD_FOLDER, fname)
            
            file.save(save_path)
            log.info(f"[UPLOAD] Saved: {fname}")
    
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/clear_data', methods=['POST'])
def clear_data():
    """Delete all uploaded files."""
    import shutil
    
    try:
        # Remove all files
        for item in os.listdir(UPLOAD_FOLDER):
            item_path = os.path.join(UPLOAD_FOLDER, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        # Recreate images directory
        os.makedirs(os.path.join(UPLOAD_FOLDER, 'images'), exist_ok=True)
        
        log.info("[CLEAR] All data cleared")
        return jsonify({'success': True, 'message': 'All data cleared successfully'})
    except Exception as e:
        log.error(f"[CLEAR] Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
