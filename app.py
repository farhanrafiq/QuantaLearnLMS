import os
import logging
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user, login_user, logout_user, UserMixin
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func, text

# Configure logging
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "quantafons-production-key-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///quantafons_lms.db"
    logging.warning("Using SQLite for development")
else:
    logging.info("Using PostgreSQL database")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db = SQLAlchemy(app, model_class=Base)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Import models after db is created
from models import *

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Role required decorator
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not any(current_user.has_role(role) for role in allowed_roles):
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Initialize database with initial data
def init_db():
    db.create_all()
    
    # Create roles
    roles_list = ['SuperAdmin', 'SchoolAdmin', 'Teacher', 'Student', 'Parent', 'TransportManager', 'Driver', 'Accountant']
    for role_name in roles_list:
        if not Role.query.filter_by(name=role_name).first():
            role = Role(name=role_name, description=f'{role_name} role')
            db.session.add(role)
    
    # Create default school
    school = School.query.first()
    if not school:
        school = School(
            name='QuantaFONS Demo School',
            address='123 Education Street',
            city='Tech City',
            state='Innovation State',
            country='Digital Nation',
            email='contact@quantafons.com',
            phone='+1-555-0123'
        )
        db.session.add(school)
        db.session.commit()
    
    # Create super admin
    if not User.query.filter_by(email='admin@quantafons.com').first():
        super_role = Role.query.filter_by(name='SuperAdmin').first()
        if super_role:
            admin_user = User(
                email='admin@quantafons.com',
                password_hash=generate_password_hash('admin123'),
                full_name='QuantaFONS Administrator',
                school_id=school.id,
                active=True
            )
            admin_user.roles.append(super_role)
            db.session.add(admin_user)
    
    # Create demo teacher
    if not User.query.filter_by(email='teacher@quantafons.com').first():
        teacher_role = Role.query.filter_by(name='Teacher').first()
        if teacher_role:
            teacher_user = User(
                email='teacher@quantafons.com',
                password_hash=generate_password_hash('teacher123'),
                full_name='John Smith',
                school_id=school.id,
                active=True
            )
            teacher_user.roles.append(teacher_role)
            db.session.add(teacher_user)
    
    # Create demo student
    if not User.query.filter_by(email='student@quantafons.com').first():
        student_role = Role.query.filter_by(name='Student').first()
        if student_role:
            student_user = User(
                email='student@quantafons.com',
                password_hash=generate_password_hash('student123'),
                full_name='Jane Doe',
                school_id=school.id,
                active=True
            )
            student_user.roles.append(student_role)
            db.session.add(student_user)
    
    # Create demo driver
    if not User.query.filter_by(email='driver@quantafons.com').first():
        driver_role = Role.query.filter_by(name='Driver').first()
        if driver_role:
            driver_user = User(
                email='driver@quantafons.com',
                password_hash=generate_password_hash('driver123'),
                full_name='Mike Wilson',
                school_id=school.id,
                active=True
            )
            driver_user.roles.append(driver_role)
            db.session.add(driver_user)
    
    db.session.commit()
    
    # Create demo bus
    driver_user = User.query.filter_by(email='driver@quantafons.com').first()
    if driver_user and not Bus.query.filter_by(name='BUS-001').first():
        bus = Bus(
            school_id=school.id,
            driver_id=driver_user.id,
            name='BUS-001',
            registration_no='REG-001',
            capacity=40,
            fuel_tank_capacity=100.0,
            is_active=True
        )
        db.session.add(bus)
        db.session.commit()
    
    logging.info("Database initialized successfully")

# Routes - Authentication
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'QuantaFONS LMS is running'
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email and password:
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                user.last_login = datetime.utcnow()
                db.session.commit()
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register')
def register():
    flash('Registration is handled by system administrator', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Routes - Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_role = current_user.get_primary_role()
    
    # Get role-specific data
    data = {
        'user_role': user_role,
        'user': current_user,
        'school': current_user.school
    }
    
    if user_role == 'SuperAdmin':
        data['total_schools'] = School.query.count()
        data['total_users'] = User.query.count()
        data['total_buses'] = Bus.query.count()
        data['recent_alerts'] = Alert.query.order_by(Alert.timestamp.desc()).limit(5).all()
    elif user_role == 'Teacher':
        data['my_courses'] = Course.query.filter_by(teacher_id=current_user.id).all()
        data['total_students'] = sum(len(course.students) for course in data['my_courses'])
        data['pending_submissions'] = Submission.query.join(Assignment).filter(
            Assignment.teacher_id == current_user.id,
            Submission.marks == None
        ).count()
    elif user_role == 'Student':
        data['enrolled_courses'] = current_user.courses_enrolled
        data['pending_assignments'] = Assignment.query.join(Course).filter(
            Course.id.in_([c.id for c in current_user.courses_enrolled]),
            Assignment.is_published == True,
            Assignment.due_date >= datetime.utcnow()
        ).all()
        data['recent_grades'] = Submission.query.filter_by(
            student_id=current_user.id
        ).filter(Submission.marks != None).order_by(Submission.graded_at.desc()).limit(5).all()
    elif user_role == 'Driver':
        data['my_bus'] = Bus.query.filter_by(driver_id=current_user.id).first()
        data['my_routes'] = Route.query.filter_by(bus_id=data['my_bus'].id).all() if data['my_bus'] else []
        data['today_alerts'] = Alert.query.filter(
            Alert.bus_id == data['my_bus'].id if data['my_bus'] else None,
            Alert.timestamp >= datetime.utcnow().date()
        ).all()
    
    return render_template('dashboard.html', **data)

# Routes - Courses
@app.route('/courses')
@login_required
def courses():
    if current_user.has_role('Teacher'):
        course_list = Course.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.has_role('Student'):
        course_list = current_user.courses_enrolled
    else:
        course_list = Course.query.filter_by(school_id=current_user.school_id).all()
    
    teachers = User.query.join(User.roles).filter(Role.name == 'Teacher').all()
    return render_template('courses.html', courses=course_list, teachers=teachers)

# Routes - Transport
@app.route('/transport')
@login_required
def transport():
    buses = Bus.query.filter_by(school_id=current_user.school_id).all()
    routes = Route.query.filter_by(school_id=current_user.school_id).all()
    return render_template('transport.html', buses=buses, routes=routes)

# Routes - Settings
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# Routes - Profile
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# Routes - Reports
@app.route('/reports')
@role_required('SuperAdmin', 'SchoolAdmin')
def reports():
    return render_template('reports.html')

# Routes - Tracking
@app.route('/tracking')
@login_required
def tracking():
    buses = Bus.query.filter_by(school_id=current_user.school_id, status='active').all()
    return render_template('tracking.html', buses=buses)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialize database when module is loaded
with app.app_context():
    init_db()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)