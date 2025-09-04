from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app_final import app, db
from models import Setting, User, School, Bus, Course
from utils import role_required
from datetime import datetime

@app.route('/settings')
@login_required
def settings_page():
    """Settings management page"""
    user_role = current_user.get_primary_role()
    
    # Get user-specific settings
    user_settings = Setting.query.filter_by(user_id=current_user.id).all()
    
    # Get school-wide settings (if user has permission)
    school_settings = []
    if user_role in ['SchoolAdmin', 'SuperAdmin']:
        school_settings = Setting.query.filter_by(
            school_id=current_user.school_id, 
            user_id=None
        ).all()
    
    # Convert settings to dictionaries for easy access
    user_settings_dict = {f"{s.category}.{s.key}": s for s in user_settings}
    school_settings_dict = {f"{s.category}.{s.key}": s for s in school_settings}
    
    return render_template('settings.html', 
                         user_role=user_role,
                         user_settings=user_settings_dict,
                         school_settings=school_settings_dict)

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user and school settings"""
    try:
        category = request.args.get('category')
        
        # Get user settings
        user_query = Setting.query.filter_by(user_id=current_user.id)
        if category:
            user_query = user_query.filter_by(category=category)
        user_settings = user_query.all()
        
        # Get school settings if user has permission
        school_settings = []
        if current_user.has_role('SchoolAdmin') or current_user.has_role('SuperAdmin'):
            school_query = Setting.query.filter_by(
                school_id=current_user.school_id,
                user_id=None
            )
            if category:
                school_query = school_query.filter_by(category=category)
            school_settings = school_query.all()
        
        return jsonify({
            'user_settings': [{
                'id': s.id,
                'category': s.category,
                'key': s.key,
                'value': s.get_value(),
                'data_type': s.data_type
            } for s in user_settings],
            'school_settings': [{
                'id': s.id,
                'category': s.category,
                'key': s.key,
                'value': s.get_value(),
                'data_type': s.data_type
            } for s in school_settings]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
@login_required
def update_setting():
    """Update or create a setting"""
    try:
        data = request.get_json()
        category = data.get('category')
        key = data.get('key')
        value = data.get('value')
        data_type = data.get('data_type', 'string')
        is_school_setting = data.get('is_school_setting', False)
        
        # Check permissions for school settings
        if is_school_setting and not (current_user.has_role('SchoolAdmin') or current_user.has_role('SuperAdmin')):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Find existing setting or create new one
        if is_school_setting:
            setting = Setting.query.filter_by(
                school_id=current_user.school_id,
                user_id=None,
                category=category,
                key=key
            ).first()
            if not setting:
                setting = Setting()
                setting.school_id = current_user.school_id
                setting.user_id = None
        else:
            setting = Setting.query.filter_by(
                user_id=current_user.id,
                category=category,
                key=key
            ).first()
            if not setting:
                setting = Setting()
                setting.user_id = current_user.id
                setting.school_id = current_user.school_id
        
        setting.category = category
        setting.key = key
        setting.data_type = data_type
        setting.set_value(value)
        setting.updated_at = datetime.utcnow()
        
        db.session.add(setting)
        db.session.commit()
        
        return jsonify({'message': 'Setting updated successfully', 'setting_id': setting.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/<int:setting_id>', methods=['DELETE'])
@login_required
def delete_setting(setting_id):
    """Delete a setting"""
    try:
        setting = Setting.query.get_or_404(setting_id)
        
        # Check permissions
        if setting.user_id and setting.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        elif setting.school_id and not setting.user_id:
            if not (current_user.has_role('SchoolAdmin') or current_user.has_role('SuperAdmin')):
                return jsonify({'error': 'Insufficient permissions'}), 403
        
        db.session.delete(setting)
        db.session.commit()
        
        return jsonify({'message': 'Setting deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def get_setting(category, key, default=None, user_id=None, school_id=None):
    """Helper function to get a setting value"""
    try:
        if user_id:
            setting = Setting.query.filter_by(
                user_id=user_id,
                category=category,
                key=key
            ).first()
        elif school_id:
            setting = Setting.query.filter_by(
                school_id=school_id,
                user_id=None,
                category=category,
                key=key
            ).first()
        else:
            # Try user setting first, then school setting
            setting = Setting.query.filter_by(
                user_id=current_user.id,
                category=category,
                key=key
            ).first()
            
            if not setting:
                setting = Setting.query.filter_by(
                    school_id=current_user.school_id,
                    user_id=None,
                    category=category,
                    key=key
                ).first()
        
        return setting.get_value() if setting else default
    except:
        return default

def set_setting(category, key, value, data_type='string', user_id=None, school_id=None):
    """Helper function to set a setting value"""
    try:
        setting = None
        if user_id:
            user = User.query.get(user_id)
            if not user:
                return False
                
            setting = Setting.query.filter_by(
                user_id=user_id,
                category=category,
                key=key
            ).first()
            if not setting:
                setting = Setting()
                setting.user_id = user_id
                setting.school_id = user.school_id
        elif school_id:
            setting = Setting.query.filter_by(
                school_id=school_id,
                user_id=None,
                category=category,
                key=key
            ).first()
            if not setting:
                setting = Setting()
                setting.school_id = school_id
                setting.user_id = None
        
        if setting:
            setting.category = category
            setting.key = key
            setting.data_type = data_type
            setting.set_value(value)
            setting.updated_at = datetime.utcnow()
        
        db.session.add(setting)
        db.session.commit()
        return True
    except:
        db.session.rollback()
        return False

# Initialize default settings for new schools
def init_default_school_settings(school_id):
    """Initialize default settings for a new school"""
    default_settings = [
        # General Settings
        ('general', 'school_timezone', 'UTC', 'string'),
        ('general', 'date_format', 'YYYY-MM-DD', 'string'),
        ('general', 'time_format', '24h', 'string'),
        ('general', 'default_language', 'en', 'string'),
        
        # LMS Settings
        ('lms', 'default_assignment_duration_days', '7', 'integer'),
        ('lms', 'max_file_upload_size_mb', '10', 'integer'),
        ('lms', 'allow_late_submissions', 'true', 'boolean'),
        ('lms', 'grade_scale', 'A-F', 'string'),
        ('lms', 'attendance_required', 'true', 'boolean'),
        
        # Transport Settings
        ('transport', 'default_fuel_alert_threshold', '20', 'integer'),
        ('transport', 'max_speed_limit_kmh', '80', 'integer'),
        ('transport', 'geofence_alert_enabled', 'true', 'boolean'),
        ('transport', 'telemetry_refresh_interval_seconds', '30', 'integer'),
        ('transport', 'fuel_efficiency_target_kmpl', '8', 'float'),
        
        # Notification Settings
        ('notification', 'email_notifications_enabled', 'true', 'boolean'),
        ('notification', 'sms_notifications_enabled', 'false', 'boolean'),
        ('notification', 'push_notifications_enabled', 'true', 'boolean'),
        ('notification', 'daily_summary_enabled', 'true', 'boolean'),
        
        # Security Settings
        ('security', 'session_timeout_minutes', '60', 'integer'),
        ('security', 'password_min_length', '8', 'integer'),
        ('security', 'require_password_complexity', 'true', 'boolean'),
        ('security', 'max_login_attempts', '5', 'integer'),
        ('security', 'lockout_duration_minutes', '15', 'integer'),
    ]
    
    for category, key, value, data_type in default_settings:
        existing = Setting.query.filter_by(
            school_id=school_id,
            user_id=None,
            category=category,
            key=key
        ).first()
        
        if not existing:
            setting = Setting()
            setting.school_id = school_id
            setting.category = category
            setting.key = key
            setting.data_type = data_type
            setting.set_value(value)
            db.session.add(setting)
    
    db.session.commit()

# Initialize default user settings
def init_default_user_settings(user_id):
    """Initialize default settings for a new user"""
    user = User.query.get(user_id)
    if not user:
        return
    
    default_settings = [
        # General Preferences
        ('preferences', 'theme', 'light', 'string'),
        ('preferences', 'dashboard_layout', 'default', 'string'),
        ('preferences', 'items_per_page', '20', 'integer'),
        ('preferences', 'email_notifications', 'true', 'boolean'),
        
        # LMS Preferences
        ('lms', 'assignment_reminder_days', '2', 'integer'),
        ('lms', 'show_grades_immediately', 'true', 'boolean'),
        ('lms', 'preferred_view', 'grid', 'string'),
        
        # Transport Preferences (for drivers and transport managers)
        ('transport', 'map_type', 'satellite', 'string'),
        ('transport', 'show_all_buses', 'false', 'boolean'),
        ('transport', 'alert_sound_enabled', 'true', 'boolean'),
    ]
    
    for category, key, value, data_type in default_settings:
        existing = Setting.query.filter_by(
            user_id=user_id,
            category=category,
            key=key
        ).first()
        
        if not existing:
            setting = Setting()
            setting.user_id = user_id
            setting.school_id = user.school_id
            setting.category = category
            setting.key = key
            setting.data_type = data_type
            setting.set_value(value)
            db.session.add(setting)
    
    db.session.commit()