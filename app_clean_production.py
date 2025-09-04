import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

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
    # Remove psql command wrapper if present
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
    
    # Relationships
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    school = db.relationship('School', backref='users')
    
    # Flask-Login required methods
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

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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

@app.route('/dashboard')
@login_required
def dashboard():
    user_role = current_user.get_primary_role()
    return render_template('dashboard.html', user_role=user_role, user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Health check route
@app.route('/health')
def health():
    return {'status': 'healthy', 'message': 'QuantaFONS LMS is running'}, 200

# Initialize database
def initialize_database():
    """Initialize database with default data"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Create roles if they don't exist
            roles_list = ['SuperAdmin', 'SchoolAdmin', 'Teacher', 'Student', 'Parent', 'TransportManager', 'Driver', 'Accountant']
            for role_name in roles_list:
                if not Role.query.filter_by(name=role_name).first():
                    role = Role(name=role_name, description=f'{role_name} role')
                    db.session.add(role)
            
            # Create default school if it doesn't exist
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
            
            # Create super admin if it doesn't exist
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
                    db.session.commit()
            
            logging.info("Database initialized successfully")
            
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        db.session.rollback()

# Initialize on first request
@app.before_first_request
def setup_database():
    initialize_database()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    with app.app_context():
        initialize_database()
    app.run(host='0.0.0.0', port=port, debug=False)