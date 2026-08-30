# FarmerQueue – Render Deployment

## Render settings
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

The app initializes SQLite automatically when Gunicorn starts.

### Important
SQLite data on Render's normal filesystem is not persistent across every redeploy/restart. This project is configured for easy deployment/testing. For production use, migrate the database to PostgreSQL or attach persistent storage where appropriate.

Set `SECRET_KEY` in Render (the included `render.yaml` can generate one automatically).
