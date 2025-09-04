import os
import logging
from app import app, db

# Configure logging for production
logging.basicConfig(level=logging.INFO)

def init_app_data():
    """Initialize application data safely for production"""
    try:
        with app.app_context():
            from models import Role, User, School, ClassRoom, Bus
            from werkzeug.security import generate_password_hash
            import secrets
            
            # Create all tables
            db.create_all()
            
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
            
            logging.info("Application data initialized successfully")
            return True
            
    except Exception as e:
        logging.error(f"Failed to initialize app data: {e}")
        return False

# Initialize data only if DATABASE_URL is properly set
if os.environ.get('DATABASE_URL'):
    init_app_data()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)