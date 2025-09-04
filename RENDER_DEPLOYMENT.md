# Render Deployment Guide

## Files Created for Render Deployment

1. **render-requirements.txt** - All Python dependencies
2. **render.yaml** - Render service configuration  
3. **main_production.py** - Production-ready application entry point

## Render Configuration

### Build Command
```
pip install -r render-requirements.txt
```

### Start Command (Choose one):

**Option 1 - Simple:**
```
gunicorn --bind 0.0.0.0:$PORT main:app
```

**Option 2 - With WebSocket support:**
```
gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class eventlet main:app
```

**Option 3 - Production entry point:**
```
gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class eventlet main_production:app
```

## Environment Variables (Set in Render Dashboard)

**Required:**
- `DATABASE_URL` = `postgresql://neondb_owner:npg_XD56fvirpumO@ep-withered-wind-adh4vjf1-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`

**Optional:**
- `SESSION_SECRET` = (auto-generated or custom)
- `MQTT_BROKER_URL` = `broker.hivemq.com`
- `MQTT_BROKER_PORT` = `1883`

## Fixed Issues

✅ **Database URL parsing error** - Added proper error handling
✅ **Application context error** - Fixed Flask app context issues  
✅ **Missing requirements** - Created comprehensive requirements file
✅ **Production safety** - Removed destructive db.drop_all()
✅ **Environment validation** - Added proper environment variable checks

## Default Login Credentials

- **Email:** admin@quantafons.com
- **Password:** admin123

## Features Ready for Production

- Real-time GPS bus tracking
- Fuel monitoring with MQTT sensors
- Complete Learning Management System
- Multi-role user management
- Background job scheduling
- Neon PostgreSQL database integration