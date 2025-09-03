from app import db
from flask_login import UserMixin
from datetime import datetime

# Association table for many-to-many relationship between users and roles
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='school', lazy='dynamic')
    buses = db.relationship('Bus', backref='school', lazy='dynamic')
    courses = db.relationship('Course', backref='school', lazy='dynamic')

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

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
        if self.roles and len(self.roles) > 0:
            return self.roles[0].name
        return None

class ClassRoom(db.Model):
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=30)
    building = db.Column(db.String(50))
    floor = db.Column(db.Integer)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'))
    credits = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = db.relationship('User', backref='courses')
    classroom = db.relationship('ClassRoom', backref='courses')
    assignments = db.relationship('Assignment', backref='course', lazy='dynamic')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic')

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    max_grade = db.Column(db.Float, default=100.0)
    instructions = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('Submission', backref='assignment', lazy='dynamic')

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='submissions')
    grader = db.relationship('User', foreign_keys=[graded_by], backref='graded_submissions')

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, completed, dropped
    final_grade = db.Column(db.Float)
    
    # Relationships
    student = db.relationship('User', backref='enrollments')

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), default='present')  # present, absent, late, excused
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='attendance_records')
    course = db.relationship('Course', backref='attendance_records')
    recorder = db.relationship('User', foreign_keys=[recorded_by])

class Bus(db.Model):
    __tablename__ = 'buses'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    registration_no = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=50)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    fuel_tank_capacity = db.Column(db.Float, default=100.0)
    api_key = db.Column(db.String(100), unique=True)  # For telemetry API access
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime)
    
    # Relationships
    driver = db.relationship('User', backref='assigned_bus')
    routes = db.relationship('Route', backref='bus', lazy='dynamic')
    telemetry = db.relationship('Telemetry', backref='bus', lazy='dynamic')

class Route(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    waypoints = db.relationship('Waypoint', backref='route', lazy='dynamic', order_by='Waypoint.sequence')

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

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    activity_type = db.Column(db.String(50), nullable=False)  # LOGIN, LOGOUT, CREATE_COURSE, SUBMIT_ASSIGNMENT, etc.
    resource_type = db.Column(db.String(50))  # COURSE, ASSIGNMENT, BUS, USER, etc.
    resource_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Relationships
    user = db.relationship('User', backref='activity_logs')
    school = db.relationship('School', backref='activity_logs')

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True, index=True)  # NULL for global settings
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # NULL for school-wide settings
    category = db.Column(db.String(50), nullable=False, index=True)  # general, notification, transport, lms, security
    key = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, float, boolean, json
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    school = db.relationship('School', backref='settings')
    user = db.relationship('User', backref='settings')
    
    def get_value(self):
        """Convert string value to proper data type"""
        if self.data_type == 'boolean':
            return self.value.lower() == 'true'
        elif self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'json':
            import json
            return json.loads(self.value)
        return self.value
    
    def set_value(self, value):
        """Set value with proper data type conversion"""
        if self.data_type == 'boolean':
            self.value = 'true' if value else 'false'
        elif self.data_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)