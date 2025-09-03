import functools
from flask import jsonify
from flask_login import current_user
from datetime import datetime, timedelta
import math

def role_required(*roles):
    """Decorator to require specific roles for accessing endpoints"""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication required"}), 401
            
            user_roles = {role.name for role in current_user.roles}
            if not any(role in user_roles for role in roles):
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def calculate_fuel_efficiency(telemetry_data):
    """Calculate fuel efficiency metrics from telemetry data"""
    if len(telemetry_data) < 2:
        return {}
    
    total_distance = 0
    total_fuel_consumed = 0
    efficiency_points = []
    
    for i in range(1, len(telemetry_data)):
        prev_data = telemetry_data[i-1]
        curr_data = telemetry_data[i]
        
        distance = 0  # Initialize distance variable
        
        # Calculate distance traveled
        if prev_data.odometer_km and curr_data.odometer_km:
            distance = curr_data.odometer_km - prev_data.odometer_km
            if distance > 0:
                total_distance += distance
        
        # Calculate fuel consumed
        if prev_data.fuel_level_liters and curr_data.fuel_level_liters:
            fuel_diff = prev_data.fuel_level_liters - curr_data.fuel_level_liters
            if fuel_diff > 0 and distance > 0:  # Only count fuel consumption, not refueling
                total_fuel_consumed += fuel_diff
                
                # Calculate efficiency for this segment
                kmpl = distance / fuel_diff
                l_per_100km = (fuel_diff / distance) * 100
                
                efficiency_points.append({
                    'timestamp': curr_data.timestamp.isoformat(),
                    'kmpl': round(kmpl, 2),
                    'l_per_100km': round(l_per_100km, 2),
                    'distance_km': round(distance, 2),
                    'fuel_consumed_l': round(fuel_diff, 2)
                })
    
    # Calculate overall efficiency
    overall_kmpl = total_distance / total_fuel_consumed if total_fuel_consumed > 0 else 0
    overall_l_per_100km = (total_fuel_consumed / total_distance) * 100 if total_distance > 0 else 0
    
    return {
        'overall_kmpl': round(overall_kmpl, 2),
        'overall_l_per_100km': round(overall_l_per_100km, 2),
        'total_distance_km': round(total_distance, 2),
        'total_fuel_consumed_l': round(total_fuel_consumed, 2),
        'efficiency_timeline': efficiency_points
    }

def detect_fuel_anomaly(prev_telemetry, curr_telemetry, bus):
    """Detect fuel anomalies like theft, refueling, excessive consumption"""
    if not prev_telemetry.fuel_level_liters or not curr_telemetry.fuel_level_liters:
        return None
    
    fuel_diff = curr_telemetry.fuel_level_liters - prev_telemetry.fuel_level_liters
    time_diff = (curr_telemetry.timestamp - prev_telemetry.timestamp).total_seconds() / 3600  # hours
    
    # Fuel refill detection (sudden increase)
    if fuel_diff > 10:  # More than 10 liters increase
        return {
            'type': 'REFUEL',
            'amount': fuel_diff,
            'details': f'Fuel refill detected: {fuel_diff:.1f}L added',
            'severity': 'INFO'
        }
    
    # Fuel theft detection (sudden decrease while stationary)
    if fuel_diff < -5 and curr_telemetry.speed_kmh == 0 and not curr_telemetry.engine_on:
        return {
            'type': 'THEFT',
            'amount': abs(fuel_diff),
            'details': f'Potential fuel theft: {abs(fuel_diff):.1f}L lost while stationary',
            'severity': 'CRITICAL'
        }
    
    # Excessive fuel consumption
    if fuel_diff < -2 and time_diff > 0:
        consumption_rate = abs(fuel_diff) / time_diff  # L/hour
        if consumption_rate > 15:  # More than 15L/hour consumption
            return {
                'type': 'EXCESSIVE_CONSUMPTION',
                'amount': abs(fuel_diff),
                'details': f'High fuel consumption: {consumption_rate:.1f}L/hour',
                'severity': 'WARNING'
            }
    
    # Idling detection (engine on, no movement, fuel consumption)
    if (curr_telemetry.speed_kmh == 0 and curr_telemetry.engine_on and 
        fuel_diff < -0.5 and time_diff > 0.5):  # 0.5L consumed in 30+ minutes while idle
        return {
            'type': 'IDLE',
            'amount': abs(fuel_diff),
            'details': f'Extended idling detected: {abs(fuel_diff):.1f}L consumed while stationary',
            'severity': 'WARNING'
        }
    
    return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

def is_point_in_geofence(lat, lon, geofence):
    """Check if a point is inside a circular geofence"""
    distance = calculate_distance(lat, lon, geofence.center_latitude, geofence.center_longitude)
    return distance <= (geofence.radius_meters / 1000)  # Convert meters to kilometers

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return "N/A"
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_date(dt):
    """Format date for display"""
    if not dt:
        return "N/A"
    return dt.strftime('%Y-%m-%d')

def get_user_dashboard_data(user):
    """Get dashboard data based on user role"""
    from models import Course, Assignment, Bus, Alert
    
    role = user.get_primary_role()
    data = {'role': role}
    
    if role == 'Teacher':
        data['courses_count'] = Course.query.filter_by(teacher_id=user.id).count()
        data['pending_assignments'] = Assignment.query.join(Course).filter(
            Course.teacher_id == user.id,
            Assignment.due_date > datetime.utcnow()
        ).count()
    
    elif role == 'Student':
        from models import Enrollment
        data['enrolled_courses'] = Enrollment.query.filter_by(student_id=user.id).count()
        data['pending_assignments'] = Assignment.query.join(Course).join(Enrollment).filter(
            Enrollment.student_id == user.id,
            Assignment.due_date > datetime.utcnow()
        ).count()
    
    elif role in ['TransportManager', 'Driver']:
        data['total_buses'] = Bus.query.filter_by(school_id=user.school_id).count()
        data['active_alerts'] = Alert.query.join(Bus).filter(
            Bus.school_id == user.school_id,
            Alert.is_acknowledged == False
        ).count()
    
    elif role in ['SchoolAdmin', 'SuperAdmin']:
        from models import User
        from models import Role, roles_users
        data['total_students'] = User.query.join(roles_users).join(Role).filter(
            User.school_id == user.school_id,
            Role.name == 'Student'
        ).count()
        data['total_teachers'] = User.query.join(roles_users).join(Role).filter(
            User.school_id == user.school_id,
            Role.name == 'Teacher'
        ).count()
        data['total_courses'] = Course.query.filter_by(school_id=user.school_id).count()
        data['total_buses'] = Bus.query.filter_by(school_id=user.school_id).count()
    
    return data

def log_activity(user_id, activity_type, description=None, resource_type=None, resource_id=None, request_obj=None):
    """Log user activity for monitoring"""
    try:
        from models import ActivityLog
        from app import db
        
        activity = ActivityLog()
        activity.user_id = user_id
        activity.school_id = current_user.school_id if current_user.is_authenticated else None
        activity.activity_type = activity_type
        activity.description = description
        activity.resource_type = resource_type
        activity.resource_id = resource_id
        
        if request_obj:
            activity.ip_address = request_obj.environ.get('HTTP_X_FORWARDED_FOR') or request_obj.environ.get('REMOTE_ADDR')
            activity.user_agent = request_obj.headers.get('User-Agent', '')[:255]
        
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        print(f"Failed to log activity: {e}")

def get_recent_activities(school_id, limit=50):
    """Get recent activities for the school"""
    try:
        from models import ActivityLog, User
        from app import db
        
        activities = db.session.query(ActivityLog, User).join(
            User, ActivityLog.user_id == User.id
        ).filter(
            ActivityLog.school_id == school_id
        ).order_by(
            ActivityLog.timestamp.desc()
        ).limit(limit).all()
        
        return [{
            'id': activity.id,
            'user_name': user.full_name,
            'activity_type': activity.activity_type,
            'description': activity.description,
            'resource_type': activity.resource_type,
            'timestamp': activity.timestamp.isoformat(),
            'ip_address': activity.ip_address
        } for activity, user in activities]
    except Exception as e:
        print(f"Failed to get activities: {e}")
        return []
