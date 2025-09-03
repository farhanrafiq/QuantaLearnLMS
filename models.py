from datetime import datetime
from flask_login import UserMixin
from app import db

# Association table for many-to-many relationship between users and roles
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    timezone = db.Column(db.String(64), default='UTC')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='school', lazy=True)
    buses = db.relationship('Bus', backref='school', lazy=True)
    routes = db.relationship('Route', backref='school', lazy=True)
    courses = db.relationship('Course', backref='school', lazy=True)
    classrooms = db.relationship('ClassRoom', backref='school', lazy=True)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    active = db.Column(db.Boolean, default=True, name='is_active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Many-to-many relationship with roles
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    
    @property
    def is_active(self):
        return self.active
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
    
    def get_primary_role(self):
        return self.roles[0].name if len(self.roles) > 0 else None

class ClassRoom(db.Model):
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(10))
    capacity = db.Column(db.Integer)
    
    # Relationships
    courses = db.relationship('Course', backref='classroom', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'))
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = db.relationship('User', backref='taught_courses')
    assignments = db.relationship('Assignment', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    attendance_records = db.relationship('Attendance', backref='course', lazy=True)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', backref='enrollments')

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    max_grade = db.Column(db.Float, default=100.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    
    # Relationships
    student = db.relationship('User', backref='submissions')

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    present = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(255))
    
    # Relationships
    student = db.relationship('User', backref='attendance_records')

# Transport Module Models
class Bus(db.Model):
    __tablename__ = 'buses'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    registration_no = db.Column(db.String(80), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=50)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Fuel tank capacity in liters
    fuel_tank_capacity = db.Column(db.Float, default=100.0)
    
    # Relationships
    driver = db.relationship('User', backref='driven_buses')
    routes = db.relationship('Route', backref='bus', lazy=True)
    telemetry_data = db.relationship('Telemetry', backref='bus', lazy=True)
    fuel_events = db.relationship('FuelEvent', backref='bus', lazy=True)
    alerts = db.relationship('Alert', backref='bus', lazy=True)

class Route(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    waypoints = db.relationship('Waypoint', backref='route', lazy=True, order_by='Waypoint.sequence')

class Waypoint(db.Model):
    __tablename__ = 'waypoints'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    stop_name = db.Column(db.String(120))
    estimated_arrival = db.Column(db.Time)
    is_pickup_point = db.Column(db.Boolean, default=True)

class Telemetry(db.Model):
    __tablename__ = 'telemetry'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    speed_kmh = db.Column(db.Float, default=0.0)
    fuel_level_liters = db.Column(db.Float)
    fuel_flow_lph = db.Column(db.Float, default=0.0)
    odometer_km = db.Column(db.Float, default=0.0)
    engine_on = db.Column(db.Boolean, default=False)
    heading = db.Column(db.Float)  # Compass heading in degrees
    altitude = db.Column(db.Float)

class FuelEvent(db.Model):
    __tablename__ = 'fuel_events'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(30), nullable=False)  # THEFT, REFUEL, IDLE, OVERSPEED, ROUTE_DEVIATION, GEOFENCE
    amount_liters = db.Column(db.Float, default=0.0)
    details = db.Column(db.Text)
    severity = db.Column(db.String(10), default='INFO')  # INFO, WARNING, CRITICAL

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(10), default='INFO')  # INFO, WARNING, CRITICAL
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text)
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    acknowledged_at = db.Column(db.DateTime)
    
    # Relationships
    acknowledger = db.relationship('User', backref='acknowledged_alerts')

class Geofence(db.Model):
    __tablename__ = 'geofences'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    center_latitude = db.Column(db.Float, nullable=False)
    center_longitude = db.Column(db.Float, nullable=False)
    radius_meters = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
