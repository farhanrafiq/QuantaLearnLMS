import os
import logging
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
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()
scheduler = BackgroundScheduler()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "quantafons-dev-secret-key-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database with better error handling
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # For development only
    database_url = "sqlite:///quantafons_lms.db"
    logging.warning("No DATABASE_URL found, using SQLite for development")
else:
    logging.info(f"Using database: {database_url[:20]}...")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
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

# Initialize database in a safer way for production
def init_database():
    try:
        with app.app_context():
            # Import models to ensure tables are created
            import models
            # Create tables if they don't exist (don't drop in production)
            db.create_all()
            logging.info("Database initialized successfully")
            return True
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return False

# Only initialize if database connection works
if init_database():
    with app.app_context():
        # Create default roles and admin user
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
    
    # Create super admin if it doesn't exist
    if not User.query.filter_by(email='admin@quantafons.com').first():
        school = School.query.filter_by(name='QuantaFONS Demo School').first()
        super_role = Role.query.filter_by(name='SuperAdmin').first()
        admin_user = User()
        admin_user.email = 'admin@quantafons.com'
        admin_user.password_hash = generate_password_hash('admin123')
        admin_user.full_name = 'QuantaFONS Administrator'
        admin_user.school_id = school.id
        admin_user.active = True
        admin_user.roles.append(super_role)
        db.session.add(admin_user)
        
        # Create sample classrooms
        from models import ClassRoom
        sample_classrooms = [
            {'name': 'Room A-101', 'capacity': 30, 'building': 'Academic Block A'},
            {'name': 'Room B-202', 'capacity': 25, 'building': 'Academic Block B'},
            {'name': 'Computer Lab 1', 'capacity': 40, 'building': 'Technology Center'},
            {'name': 'Science Lab', 'capacity': 35, 'building': 'Science Block'},
            {'name': 'Library Hall', 'capacity': 100, 'building': 'Main Building'}
        ]
        
        for classroom_data in sample_classrooms:
            if not ClassRoom.query.filter_by(name=classroom_data['name'], school_id=school.id).first():
                classroom = ClassRoom()
                classroom.name = classroom_data['name']
                classroom.capacity = classroom_data['capacity']
                classroom.building = classroom_data['building']
                classroom.school_id = school.id
                db.session.add(classroom)
        
        # Create sample buses for transport module
        from models import Bus
        import secrets
        sample_buses = [
            {'name': 'Bus Alpha', 'registration_no': 'QF-001', 'capacity': 45, 'fuel_tank_capacity': 80.0},
            {'name': 'Bus Beta', 'registration_no': 'QF-002', 'capacity': 50, 'fuel_tank_capacity': 85.0},
            {'name': 'Bus Gamma', 'registration_no': 'QF-003', 'capacity': 35, 'fuel_tank_capacity': 75.0}
        ]
        
        for bus_data in sample_buses:
            if not Bus.query.filter_by(registration_no=bus_data['registration_no'], school_id=school.id).first():
                bus = Bus()
                bus.school_id = school.id
                bus.name = bus_data['name']
                bus.registration_no = bus_data['registration_no']
                bus.capacity = bus_data['capacity']
                bus.fuel_tank_capacity = bus_data['fuel_tank_capacity']
                bus.is_active = True
                bus.api_key = secrets.token_urlsafe(32)
                db.session.add(bus)
        
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Import route modules
from auth import *
from transport import *
from lms import *
from settings import *

# Start scheduler
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Import MQTT client if available
try:
    import mqtt_client
    mqtt_client.init_mqtt(app)
except ImportError:
    logging.warning("MQTT client not available")

# Import scheduler jobs
import scheduler as sched_jobs
sched_jobs.init_scheduler(scheduler, app)
