import os
import logging
import re
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "quantafons-production-key-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

def clean_database_url(url):
    """Clean and validate database URL"""
    if not url:
        return None
    
    # Remove psql command wrapper if present
    if url.startswith("psql '") and url.endswith("'"):
        url = url[6:-1]  # Remove "psql '" from start and "'" from end
    
    # Remove any quotes
    url = url.strip('\'"')
    
    # Validate it looks like a proper PostgreSQL URL
    if url.startswith('postgresql://') or url.startswith('postgres://'):
        return url
    
    return None

# Configure the database with robust error handling
database_url = os.environ.get("DATABASE_URL")
cleaned_url = clean_database_url(database_url)

if not cleaned_url:
    # Fallback for development
    cleaned_url = "sqlite:///quantafons_lms.db"
    logging.warning("No valid DATABASE_URL found, using SQLite for development")
else:
    logging.info("Successfully configured PostgreSQL database")

app.config["SQLALCHEMY_DATABASE_URI"] = cleaned_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
socketio.init_app(app, async_mode='threading')
migrate.init_app(app, db)

# Import all modules after app initialization
from auth import *
from lms import *  
from transport import *
from settings import *
from utils import *
from models import *

# Initialize database and create default data
def initialize_app():
    """Initialize application with default data"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Only create default data in production if DATABASE_URL is set
            if os.environ.get("DATABASE_URL"):
                from models import Role, User, School
                from werkzeug.security import generate_password_hash
                
                # Create roles if they don't exist
                roles_list = ['SuperAdmin', 'SchoolAdmin', 'Teacher', 'Student', 'Parent', 'TransportManager', 'Driver', 'Accountant']
                for role_name in roles_list:
                    if not Role.query.filter_by(name=role_name).first():
                        role = Role()
                        role.name = role_name
                        db.session.add(role)
                
                # Create default school if it doesn't exist
                if not School.query.filter_by(name='QuantaFONS Demo School').first():
                    school = School()
                    school.name = 'QuantaFONS Demo School'
                    school.address = '123 Education Street'
                    school.city = 'Tech City'
                    school.state = 'Innovation State'
                    school.country = 'Digital Nation'
                    db.session.add(school)
                    db.session.commit()
                else:
                    school = School.query.filter_by(name='QuantaFONS Demo School').first()
                
                # Create super admin if it doesn't exist
                if not User.query.filter_by(email='admin@quantafons.com').first():
                    super_role = Role.query.filter_by(name='SuperAdmin').first()
                    admin_user = User()
                    admin_user.email = 'admin@quantafons.com'
                    admin_user.password_hash = generate_password_hash('admin123')
                    admin_user.full_name = 'QuantaFONS Administrator'
                    admin_user.school_id = school.id
                    admin_user.is_active = True
                    admin_user.roles.append(super_role)
                    db.session.add(admin_user)
                    db.session.commit()
                
                logging.info("Application initialized successfully with default data")
            
    except Exception as e:
        logging.error(f"Failed to initialize application: {e}")
        # Don't fail startup, just log the error

# Initialize the app
initialize_app()

# Initialize background services safely
try:
    from mqtt_client import init_mqtt_client
    init_mqtt_client()
    logging.info("MQTT client initialized")
except Exception as e:
    logging.info(f"MQTT client not available: {e}")

try:
    from utils import init_scheduler
    init_scheduler()
    logging.info("Scheduler initialized")
except Exception as e:
    logging.info(f"Scheduler not available: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)