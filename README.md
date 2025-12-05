# Drone Viewer - Render.com Deployment

Web application for viewing GPS-tagged drone images and DJI video SRT files on an interactive map.

## Features

- ✅ **500MB upload limit** (vs 100MB on PythonAnywhere)
- ✅ **Persistent storage** with Render disks (1GB free)
- ✅ GPS-tagged image visualization with Folium maps
- ✅ DJI SRT video GPS track parsing and display
- ✅ Interactive image viewer with zoom/rotate/flip (Viewer.js)
- ✅ Video playback with synchronized GPS track
- ✅ Layer controls for images, video points, tracks
- ✅ Clear data functionality

## Render.com Deployment

### Quick Deploy (Blueprint Method)

1. **Create GitHub Repository**
   - Create new repo on GitHub
   - Upload contents of `drone_viewer_render/` folder
   - Commit and push

2. **Deploy to Render**
   - Go to [render.com](https://render.com) and sign up/login
   - Click **New** → **Blueprint**
   - Connect your GitHub repository
   - Render will detect `render.yaml` and configure automatically
   - Click **Apply** to deploy

### Manual Deploy Method

1. **Create New Web Service**
   - Go to Render Dashboard
   - Click **New** → **Web Service**
   - Connect GitHub repository or upload files

2. **Configure Service**
   - **Name**: `drone-viewer`
   - **Environment**: `Python 3`
   - **Region**: `Oregon` (or nearest)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`

3. **Add Persistent Disk**
   - In service settings, go to **Disks**
   - Click **Add Disk**
   - **Name**: `uploads`
   - **Mount Path**: `/opt/render/project/src/uploads`
   - **Size**: `1 GB`
   - Click **Save**

4. **Environment Variables**
   - Go to **Environment** tab
   - Add: `PYTHON_VERSION = 3.11.0`
   - Add: `UPLOAD_FOLDER = /opt/render/project/src/uploads`

5. **Deploy**
   - Click **Manual Deploy** → **Deploy latest commit**
   - Wait 3-5 minutes for build to complete
   - Your app will be live at `https://drone-viewer-XXXX.onrender.com`

## Usage

1. **Upload Files**
   - Click **Choose Files** button in header
   - Select GPS-tagged images (.jpg, .jpeg, .png)
   - Or select video (.mp4, .mov) + SRT file (.srt)
   - Click **Upload**

2. **View on Map**
   - Images appear as blue camera markers
   - Video GPS track appears as red polyline
   - Click markers to view images in left panel

3. **Image Viewer**
   - Click map markers or thumbnail to open full image
   - Use toolbar to zoom, rotate, flip

4. **Clear Data**
   - Click **Clear All Data** button to delete all uploads
   - Confirms before deleting

## File Limits

- **Max file size**: 500MB per file
- **Total storage**: 1GB on free tier (persistent across deploys)
- **Request timeout**: 30 seconds (videos load progressively)

## Render Free Tier Limits

- ✅ 750 hours/month runtime (enough for continuous use)
- ✅ Auto-sleep after 15 min inactivity (wakes in ~30 sec)
- ✅ 1GB persistent disk storage
- ✅ Custom domain support
- ✅ Automatic SSL/HTTPS

## Troubleshooting

**App goes to sleep**: Free tier sleeps after 15 minutes of inactivity. First request after sleep takes 30-60 seconds to wake up.

**Upload fails**: Check file size is under 500MB. For very large videos, consider compressing first.

**Map doesn't show**: Check browser console for errors. Ensure images have GPS EXIF data or video has matching SRT file.

**Files disappear**: Without persistent disk configured, Render uses ephemeral storage that resets on each deploy. Make sure disk is mounted at `/opt/render/project/src/uploads`.

## Development

Run locally:
```bash
pip install -r requirements.txt
python app.py
```

Access at `http://localhost:5000`

## Tech Stack

- **Backend**: Flask 3.0, Python 3.11
- **Maps**: Folium, OpenStreetMap
- **Image Viewer**: Viewer.js
- **EXIF**: ExifRead
- **Server**: Gunicorn
- **Platform**: Render.com
