# Render.com Deployment Guide

## Why Render.com?

**Advantages over PythonAnywhere:**
- ✅ **500MB upload limit** (vs 100MB)
- ✅ **1GB persistent disk** storage (files survive deploys)
- ✅ **Auto-scaling** and better performance
- ✅ **Automatic HTTPS** and custom domains
- ✅ **Git-based deployment** (easy updates)
- ✅ **No manual WSGI configuration**

**Free Tier:**
- 750 hours/month (continuous usage possible)
- Sleeps after 15 min inactivity (wakes in ~30 sec)
- 1GB persistent storage
- Shared CPU/RAM (sufficient for this app)

## Step-by-Step Deployment

### Method 1: Blueprint (Recommended - Fastest)

1. **Prepare GitHub Repository**
   ```powershell
   cd drone_viewer_render
   git init
   git add .
   git commit -m "Initial commit - Drone Viewer for Render"
   ```

2. **Push to GitHub**
   - Create new repository on GitHub (public or private)
   - Follow GitHub's instructions to push:
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/drone-viewer-render.git
   git branch -M main
   git push -u origin main
   ```

3. **Deploy with Blueprint**
   - Go to https://render.com and sign up/login
   - Click **New** → **Blueprint**
   - Select your GitHub repository
   - Render will read `render.yaml` and show preview
   - Click **Apply** to create all resources
   - Wait 3-5 minutes for deployment
   - Your app will be at `https://drone-viewer-XXXX.onrender.com`

### Method 2: Manual Setup

1. **Create Web Service**
   - Dashboard → **New** → **Web Service**
   - Connect your GitHub account
   - Select repository and branch
   - Or choose **Public Git repository** and paste URL

2. **Configure Build**
   - **Name**: `drone-viewer` (lowercase, hyphens only)
   - **Region**: `Oregon` or closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

3. **Instance Type**
   - Select **Free** tier
   - Click **Advanced** to expand options

4. **Environment Variables**
   - Click **Add Environment Variable**
   - Add: `PYTHON_VERSION` = `3.11.0`
   - Add: `UPLOAD_FOLDER` = `/opt/render/project/src/uploads`

5. **Create Service**
   - Click **Create Web Service**
   - Wait for initial deploy (3-5 minutes)

6. **Add Persistent Disk** (IMPORTANT!)
   - After service is created, go to service **Dashboard**
   - Click **Disks** in left sidebar
   - Click **Add Disk**
   - **Name**: `uploads`
   - **Mount Path**: `/opt/render/project/src/uploads`
   - **Size**: `1 GB`
   - Click **Save**
   - Service will redeploy automatically

## Post-Deployment

### Test Your App

1. **Access URL**: `https://YOUR-SERVICE-NAME.onrender.com`
2. **Upload test image** with GPS data
3. **Upload video + SRT** file (under 500MB)
4. **Verify map displays** with markers/tracks
5. **Test image viewer** by clicking markers
6. **Test Clear Data** button

### Monitor Service

- **Logs**: Click **Logs** tab to see Flask output
- **Metrics**: View request counts, response times
- **Events**: See deploy history and status

### Update Code

1. **Make changes** to `app.py` or other files
2. **Commit and push** to GitHub:
   ```powershell
   git add .
   git commit -m "Update description"
   git push
   ```
3. **Auto-deploy**: Render detects changes and redeploys automatically
4. **Manual deploy**: Or click **Manual Deploy** in dashboard

## Persistent Storage Notes

**Important**: Without the persistent disk:
- Files uploaded will be deleted on each deploy
- Storage is ephemeral (temporary)

**With persistent disk mounted at `/opt/render/project/src/uploads`**:
- Files survive deploys and restarts
- 1GB free tier limit (expandable on paid plans)
- Backed up automatically by Render

**Check disk status**:
- Dashboard → Your Service → **Disks** tab
- Shows usage and mount path

## Custom Domain (Optional)

1. **Go to Settings** → **Custom Domain**
2. **Add your domain** (e.g., `drones.yourdomain.com`)
3. **Update DNS** with provided CNAME record
4. **Wait for SSL** certificate (automatic, ~5 min)

## Troubleshooting

### Build Fails

**Check requirements.txt versions**:
- Ensure `branca>=0.6.0,<0.7.0` (0.7.0 has Python 3.13 issues)
- Python 3.11 recommended (set via `PYTHON_VERSION` env var)

**View build logs**:
- Dashboard → **Logs** tab
- Look for pip install errors

### App Crashes on Start

**Check start command**:
- Must be `gunicorn app:app` (not `python app.py`)
- Gunicorn required for production

**Check logs**:
- Dashboard → **Logs** tab
- Look for import errors or missing dependencies

### Files Not Persisting

**Verify disk mounted**:
- Dashboard → **Disks** tab
- Confirm mount path is `/opt/render/project/src/uploads`
- Check `UPLOAD_FOLDER` env var matches mount path

**Disk not created**:
- Free tier allows 1 disk per service
- Must create manually (not in render.yaml for free tier)

### App Sleeps (Slow First Load)

**Expected behavior on free tier**:
- Sleeps after 15 minutes of no requests
- Wakes up in 30-60 seconds on first request
- Subsequent requests are instant

**Upgrade to keep alive**:
- Paid plans ($7/month) stay always-on
- Or use external monitoring service to ping every 10 min

### Upload Fails

**Check file size**:
- 500MB limit per file on Render
- 30 second request timeout (may need to increase for huge files)

**Check disk space**:
- 1GB total on free tier
- Clear old files or upgrade storage

## Cost Optimization

**Free Tier is Sufficient For**:
- Personal use
- Small teams (< 10 users)
- Occasional uploads (few times per week)

**Consider Upgrading If**:
- Need always-on (no sleep)
- Need > 1GB storage
- Need faster CPU/more RAM
- High traffic (> 1000 requests/day)

**Paid Plans Start at**:
- $7/month for Starter (always-on, 512MB RAM)
- Additional storage: $0.25/GB/month

## Security Notes

- HTTPS enabled automatically (Let's Encrypt SSL)
- Files in `/uploads` are publicly accessible via `/uploads/<filename>`
- Consider adding authentication if handling sensitive data
- Free tier has public URL (not password protected)

## Migration from PythonAnywhere

**What Changes**:
- No WSGI file needed (Gunicorn handles it)
- No virtual environment setup (automatic)
- No manual package installation
- Files persist across deploys (with disk)

**What Stays Same**:
- Same `app.py` code (minimal changes)
- Same `requirements.txt` packages
- Same Flask routes and logic

## Support

- **Render Docs**: https://render.com/docs
- **Community**: https://community.render.com
- **Status**: https://status.render.com
