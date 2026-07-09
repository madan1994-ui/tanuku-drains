# Tanuku Municipal Drainage Spray Tracker v2

## ✅ New Features Added
1. **Ward-specific login**: Staff from Ward 11 can ONLY see Ward 11 drains
2. **CSV Export**: Admin button to download full report with dates, GPS, photo filenames
3. **Secure passwords**: No more admin123

## Default Users - CHANGE AFTER FIRST LOGIN
- **Admin**: admin / Tanuku@2026 - sees all wards + dashboard
- **Ward 11**: ward11 / Ward11@2026 - only Ward 11 drains
- **Ward 12**: ward12 / Ward12@2026 - only Ward 12 drains  
- **Ward 13**: ward13 / Ward13@2026 - only Ward 13 drains
- **General Staff**: staff / Staff@2026 - sees all wards

## Setup - 3 Minutes
1. Install: `pip install -r requirements.txt`
2. Run: `python app.py`
3. Open on phone: `http://YOUR-PC-IP:5000`

Add to home screen on phone for app-like experience.

## How It Works
**Staff flow**: Login → See only their ward drains → Tap drain → Camera opens → Take photo → GPS auto-captured → Upload

**Admin flow**: Login → Dashboard shows ward-wise % complete → Download CSV button → Get full Excel with all photos + GPS + dates

## Your Data
49 drains from Wards 11, 12, 13 already imported from drains.xlsx

## Deploy Free on Render.com
1. Push this folder to GitHub
2. Go to Render.com → New Web Service → Connect repo
3. Start command: `python app.py`
4. Share the URL with staff: `https://tanuku-drains.onrender.com`

## To Add More Ward Users
Edit app.py line 42-45 and add: 
`c.execute("INSERT OR IGNORE INTO users (username, password, role, ward) VALUES ('ward14', 'Ward14@2026', 'staff', '14')")`

## Security Notes
1. Change app.secret_key in app.py line 10
2. Change all passwords after first login
3. For production, use HTTPS via Render.com or Cloudflare Tunnel
