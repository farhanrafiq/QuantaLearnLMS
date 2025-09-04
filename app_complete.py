import os
import logging
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
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
def clean_database_url(url):
    if not url:
        return None
    if url.startswith("psql '") and url.endswith("'"):
        url = url[6:-1]
    url = url.strip('\'"')
    if url.startswith('postgresql://') or url.startswith('postgres://'):
        return url
    return None

database_url = os.environ.get("DATABASE_URL")
cleaned_url = clean_database_url(database_url)

if not cleaned_url:
    cleaned_url = "sqlite:///quantafons_lms.db"
    logging.warning("Using SQLite for development")
else:
    logging.info("Using PostgreSQL database")

app.config["SQLALCHEMY_DATABASE_URI"] = cleaned_url
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

# Models
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

course_students = db.Table('course_students',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    country = db.Column(db.String(50))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    school = db.relationship('School', backref='users')
    courses_teaching = db.relationship('Course', backref='teacher', foreign_keys='Course.teacher_id')
    courses_enrolled = db.relationship('Course', secondary=course_students, backref='students')
    assignments_created = db.relationship('Assignment', backref='teacher', foreign_keys='Assignment.teacher_id')
    submissions = db.relationship('Submission', backref='student', foreign_keys='Submission.student_id')
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return self.active
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
    
    def get_primary_role(self):
        if self.roles:
            return self.roles[0].name
        return 'User'

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    code = db.Column(db.String(20))
    credits = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    assignments = db.relationship('Assignment', backref='course', lazy='dynamic')
    school = db.relationship('School', backref='courses')

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    total_marks = db.Column(db.Integer, default=100)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    submissions = db.relationship('Submission', backref='assignment', lazy='dynamic')

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    marks = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    graded_at = db.Column(db.DateTime)

class Bus(db.Model):
    __tablename__ = 'buses'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    number = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=40)
    model = db.Column(db.String(100))
    fuel_capacity = db.Column(db.Float, default=100.0)
    current_fuel = db.Column(db.Float, default=50.0)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    status = db.Column(db.String(20), default='offline')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    school = db.relationship('School', backref='buses')
    driver = db.relationship('User', backref='bus_driving')

class Route(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'))
    name = db.Column(db.String(100), nullable=False)
    start_location = db.Column(db.String(200))
    end_location = db.Column(db.String(200))
    waypoints = db.Column(db.Text)
    distance = db.Column(db.Float)
    estimated_time = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    
    school = db.relationship('School', backref='routes')
    bus = db.relationship('Bus', backref='routes')

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'))
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text)
    severity = db.Column(db.String(20), default='info')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    school = db.relationship('School', backref='alerts')
    bus = db.relationship('Bus', backref='alerts')

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

# Initialize database
_db_initialized = False

def ensure_database():
    global _db_initialized
    if _db_initialized:
        return
    
    try:
        db.create_all()
        
        # Run migrations for PostgreSQL to ensure all columns exist
        if 'postgresql' in str(db.engine.url) or 'postgres' in str(db.engine.url):
            migrations = [
                # Schools table
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS city VARCHAR(100);",
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS state VARCHAR(100);",
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS country VARCHAR(100);",
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS phone VARCHAR(30);",
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS email VARCHAR(120);",
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS website VARCHAR(200);",
                "ALTER TABLE schools ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
                # Users table
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30);",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;",
                # Courses table
                "ALTER TABLE courses ADD COLUMN IF NOT EXISTS code VARCHAR(20);",
                "ALTER TABLE courses ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 3;",
                "ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
                # Buses table
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS number VARCHAR(50);",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS model VARCHAR(100);",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS fuel_capacity FLOAT DEFAULT 100.0;",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS current_fuel FLOAT DEFAULT 50.0;",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS lat FLOAT;",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS lng FLOAT;",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'offline';",
                "ALTER TABLE buses ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
                # Fix buses table name column issue
                "ALTER TABLE buses ALTER COLUMN name DROP NOT NULL;",
                # Routes table
                "ALTER TABLE routes ADD COLUMN IF NOT EXISTS start_location VARCHAR(255);",
                "ALTER TABLE routes ADD COLUMN IF NOT EXISTS end_location VARCHAR(255);",
                "ALTER TABLE routes ADD COLUMN IF NOT EXISTS waypoints TEXT;",
                "ALTER TABLE routes ADD COLUMN IF NOT EXISTS distance FLOAT;",
                "ALTER TABLE routes ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
                # Assignments table
                "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS due_date TIMESTAMP;",
                "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS max_points INTEGER DEFAULT 100;",
                "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            ]
            
            with db.engine.connect() as conn:
                for migration in migrations:
                    try:
                        conn.execute(text(migration))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        pass  # Column already exists or table doesn't exist yet
        
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
        if driver_user and not Bus.query.filter_by(number='BUS-001').first():
            bus = Bus(
                school_id=school.id,
                driver_id=driver_user.id,
                number='BUS-001',
                capacity=40,
                model='Mercedes-Benz Sprinter',
                fuel_capacity=100.0,
                current_fuel=75.0,
                status='active'
            )
            db.session.add(bus)
            db.session.commit()
        
        _db_initialized = True
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        db.session.rollback()

# Routes - Authentication
@app.route('/')
def index():
    ensure_database()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    ensure_database()
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

# Routes - User Management
@app.route('/users')
@role_required('SuperAdmin', 'SchoolAdmin')
def users():
    all_users = User.query.filter_by(school_id=current_user.school_id).all()
    roles = Role.query.all()
    return render_template('users.html', users=all_users, roles=roles)

@app.route('/users/add', methods=['POST'])
@role_required('SuperAdmin', 'SchoolAdmin')
def add_user():
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    role_id = request.form.get('role_id')
    password = request.form.get('password', 'password123')
    
    if User.query.filter_by(email=email).first():
        flash('User with this email already exists', 'error')
        return redirect(url_for('users'))
    
    user = User(
        email=email,
        full_name=full_name,
        password_hash=generate_password_hash(password),
        school_id=current_user.school_id,
        active=True
    )
    
    role = Role.query.get(role_id)
    if role:
        user.roles.append(role)
    
    db.session.add(user)
    db.session.commit()
    flash('User added successfully', 'success')
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/toggle')
@role_required('SuperAdmin', 'SchoolAdmin')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.active = not user.active
    db.session.commit()
    status = 'activated' if user.active else 'deactivated'
    flash(f'User {status} successfully', 'success')
    return redirect(url_for('users'))

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

@app.route('/courses/add', methods=['POST'])
@role_required('SuperAdmin', 'SchoolAdmin', 'Teacher')
def add_course():
    name = request.form.get('name')
    code = request.form.get('code')
    description = request.form.get('description')
    teacher_id = request.form.get('teacher_id', current_user.id)
    
    course = Course(
        name=name,
        code=code,
        description=description,
        teacher_id=teacher_id,
        school_id=current_user.school_id,
        is_active=True
    )
    db.session.add(course)
    db.session.commit()
    flash('Course added successfully', 'success')
    return redirect(url_for('courses'))

@app.route('/courses/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    if current_user.has_role('Student'):
        submissions = {s.assignment_id: s for s in Submission.query.filter_by(
            student_id=current_user.id,
            assignment_id=Assignment.id
        ).join(Assignment).filter(Assignment.course_id == course_id).all()}
    else:
        submissions = {}
    
    return render_template('course_detail.html', course=course, assignments=assignments, submissions=submissions)

@app.route('/courses/<int:course_id>/enroll', methods=['POST'])
@role_required('Student')
def enroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course not in current_user.courses_enrolled:
        current_user.courses_enrolled.append(course)
        db.session.commit()
        flash('Enrolled successfully', 'success')
    else:
        flash('Already enrolled in this course', 'info')
    return redirect(url_for('course_detail', course_id=course_id))

# Routes - Assignments
@app.route('/assignments/add', methods=['POST'])
@role_required('Teacher')
def add_assignment():
    course_id = request.form.get('course_id')
    title = request.form.get('title')
    description = request.form.get('description')
    due_date = request.form.get('due_date')
    total_marks = request.form.get('total_marks', 100)
    
    assignment = Assignment(
        course_id=course_id,
        teacher_id=current_user.id,
        title=title,
        description=description,
        due_date=datetime.strptime(due_date, '%Y-%m-%d') if due_date else None,
        total_marks=int(total_marks),
        is_published=True
    )
    db.session.add(assignment)
    db.session.commit()
    flash('Assignment created successfully', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/assignments/<int:assignment_id>/submit', methods=['POST'])
@role_required('Student')
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    content = request.form.get('content')
    
    submission = Submission.query.filter_by(
        assignment_id=assignment_id,
        student_id=current_user.id
    ).first()
    
    if not submission:
        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id
        )
    
    submission.content = content
    submission.submitted_at = datetime.utcnow()
    
    db.session.add(submission)
    db.session.commit()
    flash('Assignment submitted successfully', 'success')
    return redirect(url_for('course_detail', course_id=assignment.course_id))

@app.route('/submissions/<int:submission_id>/grade', methods=['POST'])
@role_required('Teacher')
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    marks = request.form.get('marks')
    feedback = request.form.get('feedback')
    
    submission.marks = int(marks) if marks else None
    submission.feedback = feedback
    submission.graded_at = datetime.utcnow()
    
    db.session.commit()
    flash('Submission graded successfully', 'success')
    return redirect(request.referrer or url_for('dashboard'))

# Routes - Transport
@app.route('/transport')
@login_required
def transport():
    buses = Bus.query.filter_by(school_id=current_user.school_id).all()
    routes = Route.query.filter_by(school_id=current_user.school_id).all()
    alerts = Alert.query.filter_by(school_id=current_user.school_id).order_by(Alert.created_at.desc()).limit(10).all()
    
    return render_template('transport.html', buses=buses, routes=routes, alerts=alerts)

@app.route('/transport/buses/add', methods=['POST'])
@role_required('SuperAdmin', 'SchoolAdmin', 'TransportManager')
def add_bus():
    number = request.form.get('number')
    model = request.form.get('model')
    capacity = request.form.get('capacity', 40)
    driver_id = request.form.get('driver_id')
    
    bus = Bus(
        school_id=current_user.school_id,
        number=number,
        model=model,
        capacity=int(capacity),
        driver_id=int(driver_id) if driver_id else None,
        status='offline'
    )
    db.session.add(bus)
    db.session.commit()
    flash('Bus added successfully', 'success')
    return redirect(url_for('transport'))

@app.route('/transport/routes/add', methods=['POST'])
@role_required('SuperAdmin', 'SchoolAdmin', 'TransportManager')
def add_route():
    name = request.form.get('name')
    bus_id = request.form.get('bus_id')
    start_location = request.form.get('start_location')
    end_location = request.form.get('end_location')
    waypoints = request.form.get('waypoints')
    
    route = Route(
        school_id=current_user.school_id,
        name=name,
        bus_id=int(bus_id) if bus_id else None,
        start_location=start_location,
        end_location=end_location,
        waypoints=waypoints,
        is_active=True
    )
    db.session.add(route)
    db.session.commit()
    flash('Route added successfully', 'success')
    return redirect(url_for('transport'))

# Routes - GPS Tracking
@app.route('/tracking')
@login_required
def tracking():
    buses = Bus.query.filter_by(school_id=current_user.school_id, status='active').all()
    return render_template('tracking.html', buses=buses)

@app.route('/tracking/map')
@login_required
def tracking_map():
    buses = Bus.query.filter_by(school_id=current_user.school_id).all()
    bus_data = [{
        'id': bus.id,
        'number': bus.number,
        'lat': bus.lat or 0,
        'lng': bus.lng or 0,
        'status': bus.status,
        'fuel': bus.current_fuel,
        'driver': bus.driver.full_name if bus.driver else 'Unassigned'
    } for bus in buses]
    return render_template('tracking_map.html', buses=bus_data)

# Routes - Reports
@app.route('/reports')
@login_required
def reports():
    data = {
        'total_users': User.query.filter_by(school_id=current_user.school_id).count(),
        'total_courses': Course.query.filter_by(school_id=current_user.school_id).count(),
        'total_buses': Bus.query.filter_by(school_id=current_user.school_id).count(),
        'active_buses': Bus.query.filter_by(school_id=current_user.school_id, status='active').count(),
        'total_alerts': Alert.query.filter_by(school_id=current_user.school_id).count(),
        'recent_users': User.query.filter_by(school_id=current_user.school_id).order_by(User.created_at.desc()).limit(5).all()
    }
    return render_template('reports.html', **data)

# Routes - Profile
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    current_user.full_name = request.form.get('full_name', current_user.full_name)
    current_user.phone = request.form.get('phone', current_user.phone)
    
    if request.form.get('new_password'):
        current_password = request.form.get('current_password')
        if check_password_hash(current_user.password_hash, current_password):
            current_user.password_hash = generate_password_hash(request.form.get('new_password'))
        else:
            flash('Current password is incorrect', 'error')
            return redirect(url_for('profile'))
    
    db.session.commit()
    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))

# Routes - Settings
@app.route('/settings')
@role_required('SuperAdmin', 'SchoolAdmin')
def settings():
    return render_template('settings.html', school=current_user.school)

@app.route('/settings/school/update', methods=['POST'])
@role_required('SuperAdmin', 'SchoolAdmin')
def update_school():
    school = current_user.school
    school.name = request.form.get('name', school.name)
    school.address = request.form.get('address', school.address)
    school.city = request.form.get('city', school.city)
    school.state = request.form.get('state', school.state)
    school.country = request.form.get('country', school.country)
    school.phone = request.form.get('phone', school.phone)
    school.email = request.form.get('email', school.email)
    school.website = request.form.get('website', school.website)
    
    db.session.commit()
    flash('School settings updated successfully', 'success')
    return redirect(url_for('settings'))

# API Routes - Transport
@app.route('/api/buses/<int:bus_id>/location', methods=['POST'])
@login_required
def update_bus_location(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    data = request.get_json()
    
    bus.lat = data.get('lat')
    bus.lng = data.get('lng')
    bus.status = 'active'
    bus.last_updated = datetime.utcnow()
    
    db.session.commit()
    
    # Emit real-time update
    socketio.emit('bus_update', {
        'id': bus.id,
        'lat': bus.lat,
        'lng': bus.lng,
        'status': bus.status
    }, room=f'school_{bus.school_id}')
    
    return jsonify({'success': True})

@app.route('/api/buses/<int:bus_id>/fuel', methods=['POST'])
@login_required
def update_bus_fuel(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    data = request.get_json()
    
    bus.current_fuel = data.get('fuel', bus.current_fuel)
    bus.last_updated = datetime.utcnow()
    
    # Create alert if fuel is low
    if bus.current_fuel < 20:
        alert = Alert(
            school_id=bus.school_id,
            bus_id=bus.id,
            type='fuel_low',
            message=f'Low fuel warning for {bus.number}: {bus.current_fuel}%',
            severity='warning'
        )
        db.session.add(alert)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    alerts = Alert.query.filter_by(
        school_id=current_user.school_id
    ).order_by(Alert.created_at.desc()).limit(20).all()
    
    return jsonify([{
        'id': alert.id,
        'type': alert.type,
        'message': alert.message,
        'severity': alert.severity,
        'created_at': alert.created_at.isoformat()
    } for alert in alerts])

@app.route('/api/stats')
@login_required
def api_stats():
    stats = {
        'total_users': User.query.filter_by(school_id=current_user.school_id).count(),
        'total_courses': Course.query.filter_by(school_id=current_user.school_id).count(),
        'total_buses': Bus.query.filter_by(school_id=current_user.school_id).count(),
        'active_buses': Bus.query.filter_by(school_id=current_user.school_id, status='active').count(),
        'total_assignments': Assignment.query.join(Course).filter(Course.school_id == current_user.school_id).count(),
        'total_submissions': Submission.query.join(Assignment).join(Course).filter(Course.school_id == current_user.school_id).count()
    }
    return jsonify(stats)

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'school_{current_user.school_id}')
        emit('connected', {'message': 'Connected to real-time updates'})

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f'school_{current_user.school_id}')

@socketio.on('track_bus')
def handle_track_bus(data):
    bus_id = data.get('bus_id')
    join_room(f'bus_{bus_id}')
    emit('tracking_started', {'bus_id': bus_id})

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'QuantaFONS LMS is running',
        'timestamp': datetime.utcnow().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    with app.app_context():
        ensure_database()
    socketio.run(app, host='0.0.0.0', port=port, debug=False)