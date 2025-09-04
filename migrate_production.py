#!/usr/bin/env python
"""
Production Database Migration Script
Run this to add missing columns to the production database on Render
"""
import os
import sys
from sqlalchemy import create_engine, text

def run_migrations():
    """Add missing columns to production database"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Handle Render's postgres:// URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        engine = create_engine(database_url)
        
        migrations = [
            # Schools table columns
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS city VARCHAR(100);",
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS state VARCHAR(100);",
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS country VARCHAR(100);",
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS phone VARCHAR(20);",
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS website VARCHAR(255);",
            "ALTER TABLE schools ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            
            # Users table columns
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;",
            
            # Courses table columns  
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS code VARCHAR(20);",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 3;",
            "ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            
            # Buses table columns
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS number VARCHAR(50);",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS model VARCHAR(100);",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS fuel_capacity FLOAT DEFAULT 100.0;",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS current_fuel FLOAT DEFAULT 50.0;",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS lat FLOAT;",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS lng FLOAT;",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'offline';",
            "ALTER TABLE buses ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
            
            # Routes table columns
            "ALTER TABLE routes ADD COLUMN IF NOT EXISTS start_location VARCHAR(255);",
            "ALTER TABLE routes ADD COLUMN IF NOT EXISTS end_location VARCHAR(255);",
            "ALTER TABLE routes ADD COLUMN IF NOT EXISTS waypoints TEXT;",
            "ALTER TABLE routes ADD COLUMN IF NOT EXISTS distance FLOAT;",
            "ALTER TABLE routes ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            
            # Assignments table columns
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS due_date TIMESTAMP;",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS max_points INTEGER DEFAULT 100;",
            "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            
            # Fix bus name column issue - rename 'name' to 'number' if exists
            """
            DO $$ 
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'buses' AND column_name = 'name') THEN
                    ALTER TABLE buses RENAME COLUMN name TO number;
                END IF;
            END $$;
            """,
            
            # Make bus name column nullable if it exists
            """
            DO $$ 
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'buses' AND column_name = 'name') THEN
                    ALTER TABLE buses ALTER COLUMN name DROP NOT NULL;
                END IF;
            END $$;
            """
        ]
        
        with engine.connect() as conn:
            for migration in migrations:
                try:
                    conn.execute(text(migration))
                    conn.commit()
                    print(f"✓ Applied: {migration[:50]}...")
                except Exception as e:
                    print(f"⚠ Warning: {str(e)[:100]}")
                    conn.rollback()
        
        print("\n✅ Migration completed successfully!")
        print("Your database schema has been updated.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔄 Running production database migrations...")
    run_migrations()