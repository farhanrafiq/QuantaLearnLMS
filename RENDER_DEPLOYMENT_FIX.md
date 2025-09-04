# Fix Render Deployment Database Issues

## The Problem
Your production database on Render is missing some columns that the application expects. This is causing the error you're seeing.

## Quick Fix Solution

### Option 1: Run Migration Script (Recommended)
1. Go to your Render Dashboard
2. Navigate to your web service
3. Click on the "Shell" tab
4. Run this command:
```bash
python migrate_production.py
```

### Option 2: Manual SQL Commands
If the migration script doesn't work, you can run these SQL commands directly:

1. Go to Render Dashboard → Your Database
2. Click "Connect" → "PSQL Command"  
3. Run these commands one by one:

```sql
-- Add missing columns to schools table
ALTER TABLE schools ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE schools ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE schools ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE schools ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE schools ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE schools ADD COLUMN IF NOT EXISTS website VARCHAR(255);
ALTER TABLE schools ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add missing columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

-- Add missing columns to courses table
ALTER TABLE courses ADD COLUMN IF NOT EXISTS code VARCHAR(20);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 3;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add missing columns to buses table
ALTER TABLE buses ADD COLUMN IF NOT EXISTS number VARCHAR(50);
ALTER TABLE buses ADD COLUMN IF NOT EXISTS model VARCHAR(100);
ALTER TABLE buses ADD COLUMN IF NOT EXISTS fuel_capacity FLOAT DEFAULT 100.0;
ALTER TABLE buses ADD COLUMN IF NOT EXISTS current_fuel FLOAT DEFAULT 50.0;
ALTER TABLE buses ADD COLUMN IF NOT EXISTS lat FLOAT;
ALTER TABLE buses ADD COLUMN IF NOT EXISTS lng FLOAT;
ALTER TABLE buses ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'offline';
ALTER TABLE buses ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add missing columns to routes table
ALTER TABLE routes ADD COLUMN IF NOT EXISTS start_location VARCHAR(255);
ALTER TABLE routes ADD COLUMN IF NOT EXISTS end_location VARCHAR(255);
ALTER TABLE routes ADD COLUMN IF NOT EXISTS waypoints TEXT;
ALTER TABLE routes ADD COLUMN IF NOT EXISTS distance FLOAT;
ALTER TABLE routes ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add missing columns to assignments table
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS due_date TIMESTAMP;
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS max_points INTEGER DEFAULT 100;
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
```

### Option 3: Reset Database (Last Resort)
If you want to start fresh with a clean database:

1. **WARNING**: This will delete all data!
2. In Render Dashboard, go to your database
3. Run this to drop and recreate all tables:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
4. Then redeploy your service - it will create fresh tables

## After Fixing

Your application should work perfectly at: https://quantalearnlms.onrender.com

## Test Accounts
Once the database is fixed, you can use these accounts:
- **SuperAdmin**: admin@quantafons.com / admin123
- **Teacher**: teacher@quantafons.com / teacher123
- **Student**: student@quantafons.com / student123
- **Driver**: driver@quantafons.com / driver123

## Need Help?
If you still see errors after running the migrations, the issue might be with the initial data seeding. Let me know and I can help you fix that too!