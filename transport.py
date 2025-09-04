from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit
from app_final import app, db, socketio
from models import Bus, Route, Waypoint, Telemetry, FuelEvent, Alert, Geofence
from utils import role_required, calculate_fuel_efficiency, detect_fuel_anomaly
from datetime import datetime, timedelta
import json
import secrets
import logging

@app.route('/transport')
@login_required
@role_required('TransportManager', 'SchoolAdmin', 'SuperAdmin', 'Driver')
def transport_dashboard():
    school_buses = Bus.query.filter_by(school_id=current_user.school_id).all()
    active_routes = Route.query.filter_by(school_id=current_user.school_id, is_active=True).all()
    recent_alerts = Alert.query.join(Bus).filter(
        Bus.school_id == current_user.school_id,
        Alert.is_acknowledged == False
    ).order_by(Alert.timestamp.desc()).limit(10).all()
    
    return render_template('transport.html', 
                         buses=school_buses, 
                         routes=active_routes, 
                         alerts=recent_alerts)

@app.route('/api/transport/buses')
@login_required
def get_buses():
    buses = Bus.query.filter_by(school_id=current_user.school_id).all()
    buses_data = []
    
    for bus in buses:
        # Get latest telemetry
        latest_telemetry = Telemetry.query.filter_by(bus_id=bus.id).order_by(Telemetry.timestamp.desc()).first()
        
        bus_data = {
            'id': bus.id,
            'name': bus.name,
            'registration_no': bus.registration_no,
            'capacity': bus.capacity,
            'is_active': bus.is_active,
            'driver_name': bus.driver.full_name if bus.driver else None,
            'fuel_tank_capacity': bus.fuel_tank_capacity,
            'latest_location': {
                'latitude': latest_telemetry.latitude if latest_telemetry else None,
                'longitude': latest_telemetry.longitude if latest_telemetry else None,
                'speed': latest_telemetry.speed_kmh if latest_telemetry else 0,
                'fuel_level': latest_telemetry.fuel_level_liters if latest_telemetry else 0,
                'engine_on': latest_telemetry.engine_on if latest_telemetry else False,
                'timestamp': latest_telemetry.timestamp.isoformat() if latest_telemetry else None
            }
        }
        buses_data.append(bus_data)
    
    return jsonify(buses_data)

@app.route('/api/transport/buses', methods=['POST'])
@login_required
@role_required('TransportManager', 'SchoolAdmin', 'SuperAdmin')
def create_bus():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        name = data.get('name')
        registration_no = data.get('registration_no')
        
        if not name or not registration_no:
            return jsonify({'error': 'Bus name and registration number required'}), 400
        
        # Check if registration number already exists in school
        existing_bus = Bus.query.filter_by(
            registration_no=registration_no,
            school_id=current_user.school_id
        ).first()
        if existing_bus:
            return jsonify({'error': 'Registration number already exists'}), 400
        
        capacity = data.get('capacity', 50)
        fuel_tank_capacity = data.get('fuel_tank_capacity', 100.0)
        
        if capacity < 1 or capacity > 200:
            return jsonify({'error': 'Invalid capacity value'}), 400
        if fuel_tank_capacity < 10 or fuel_tank_capacity > 1000:
            return jsonify({'error': 'Invalid fuel tank capacity'}), 400
        
        # Generate unique API key for the bus
        api_key = secrets.token_urlsafe(32)
        
        bus = Bus()
        bus.school_id = current_user.school_id
        bus.name = name.strip()
        bus.registration_no = registration_no.strip().upper()
        bus.capacity = capacity
        bus.api_key = api_key
        bus.fuel_tank_capacity = fuel_tank_capacity
        
        db.session.add(bus)
        db.session.commit()
        
        return jsonify({
            'message': 'Bus created successfully',
            'bus_id': bus.id,
            'api_key': api_key
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating bus: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/transport/telemetry/<int:bus_id>', methods=['POST'])
def receive_telemetry(bus_id):
    try:
        # Verify API key
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
            
        bus = Bus.query.filter_by(id=bus_id, api_key=api_key).first()
        if not bus:
            return jsonify({'error': 'Invalid bus ID or API key'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
    
        # Validate telemetry data
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is not None and (latitude < -90 or latitude > 90):
            return jsonify({'error': 'Invalid latitude value'}), 400
        if longitude is not None and (longitude < -180 or longitude > 180):
            return jsonify({'error': 'Invalid longitude value'}), 400
            
        speed_kmh = data.get('speed_kmh', 0)
        if speed_kmh < 0 or speed_kmh > 200:
            return jsonify({'error': 'Invalid speed value'}), 400
            
        fuel_level = data.get('fuel_level_liters')
        if fuel_level is not None and (fuel_level < 0 or fuel_level > bus.fuel_tank_capacity * 1.1):
            return jsonify({'error': 'Invalid fuel level value'}), 400
        
        # Create telemetry record
        telemetry = Telemetry()
        telemetry.bus_id = bus_id
        telemetry.latitude = latitude
        telemetry.longitude = longitude
        telemetry.speed_kmh = speed_kmh
        telemetry.fuel_level_liters = fuel_level
        telemetry.fuel_flow_lph = max(0, data.get('fuel_flow_lph', 0))
        telemetry.odometer_km = max(0, data.get('odometer_km', 0))
        telemetry.engine_on = bool(data.get('engine_on', False))
        telemetry.heading = data.get('heading')
        telemetry.altitude = data.get('altitude')
        
        db.session.add(telemetry)
        
        # Analyze fuel data for anomalies
        previous_telemetry = Telemetry.query.filter_by(bus_id=bus_id).order_by(Telemetry.timestamp.desc()).offset(1).first()
        
        if previous_telemetry:
            fuel_anomaly = detect_fuel_anomaly(previous_telemetry, telemetry, bus)
            if fuel_anomaly:
                fuel_event = FuelEvent()
                fuel_event.bus_id = bus_id
                fuel_event.event_type = fuel_anomaly['type']
                fuel_event.amount_liters = fuel_anomaly.get('amount', 0)
                fuel_event.details = fuel_anomaly.get('details', '')
                fuel_event.severity = fuel_anomaly.get('severity', 'INFO')
                db.session.add(fuel_event)
                
                # Create alert for critical events
                if fuel_anomaly['severity'] in ['WARNING', 'CRITICAL']:
                    alert = Alert()
                    alert.bus_id = bus_id
                    alert.level = fuel_anomaly['severity']
                    alert.title = f"Fuel {fuel_anomaly['type'].title()} Detected"
                    alert.message = fuel_anomaly.get('details', '')
                    db.session.add(alert)
        
        # Check for other alerts (speed, geofence, etc.)
        try:
            check_alerts(telemetry, bus)
        except Exception as alert_error:
            logging.warning(f"Alert check failed for bus {bus_id}: {alert_error}")
        
        db.session.commit()
        
        # Emit real-time update via SocketIO
        try:
            socketio.emit('telemetry_update', {
                'bus_id': bus_id,
                'latitude': telemetry.latitude,
                'longitude': telemetry.longitude,
                'speed_kmh': telemetry.speed_kmh,
                'fuel_level_liters': telemetry.fuel_level_liters,
                'engine_on': telemetry.engine_on,
                'timestamp': telemetry.timestamp.isoformat()
            }, to=f'school_{bus.school_id}')
        except Exception as socket_error:
            logging.warning(f"SocketIO emit failed: {socket_error}")
        
        return jsonify({'message': 'Telemetry received successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error processing telemetry for bus {bus_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/transport/fuel-analytics/<int:bus_id>')
@login_required
def get_fuel_analytics(bus_id):
    # Verify bus belongs to user's school
    bus = Bus.query.filter_by(id=bus_id, school_id=current_user.school_id).first()
    if not bus:
        return jsonify({'error': 'Bus not found'}), 404
    
    # Get telemetry data for the last 30 days
    start_date = datetime.utcnow() - timedelta(days=30)
    telemetry_data = Telemetry.query.filter(
        Telemetry.bus_id == bus_id,
        Telemetry.timestamp >= start_date
    ).order_by(Telemetry.timestamp).all()
    
    if len(telemetry_data) < 2:
        return jsonify({'error': 'Insufficient data for analysis'}), 400
    
    # Calculate fuel efficiency metrics
    efficiency_data = calculate_fuel_efficiency(telemetry_data)
    
    # Get recent fuel events
    fuel_events = FuelEvent.query.filter(
        FuelEvent.bus_id == bus_id,
        FuelEvent.timestamp >= start_date
    ).order_by(FuelEvent.timestamp.desc()).all()
    
    events_data = [{
        'timestamp': event.timestamp.isoformat(),
        'type': event.event_type,
        'amount_liters': event.amount_liters,
        'details': event.details,
        'severity': event.severity
    } for event in fuel_events]
    
    return jsonify({
        'bus_name': bus.name,
        'efficiency': efficiency_data,
        'events': events_data
    })

@app.route('/api/transport/routes')
@login_required
def get_routes():
    routes = Route.query.filter_by(school_id=current_user.school_id).all()
    routes_data = []
    
    for route in routes:
        waypoints = [{
            'latitude': wp.latitude,
            'longitude': wp.longitude,
            'stop_name': wp.stop_name,
            'sequence': wp.sequence,
            'estimated_arrival': wp.estimated_arrival.strftime('%H:%M') if wp.estimated_arrival else None
        } for wp in route.waypoints]
        
        routes_data.append({
            'id': route.id,
            'name': route.name,
            'description': route.description,
            'bus_name': route.bus.name if route.bus else None,
            'is_active': route.is_active,
            'waypoints': waypoints
        })
    
    return jsonify(routes_data)

@app.route('/api/transport/alerts')
@login_required
def get_alerts():
    alerts = Alert.query.join(Bus).filter(
        Bus.school_id == current_user.school_id
    ).order_by(Alert.timestamp.desc()).limit(50).all()
    
    alerts_data = [{
        'id': alert.id,
        'bus_name': alert.bus.name,
        'timestamp': alert.timestamp.isoformat(),
        'level': alert.level,
        'title': alert.title,
        'message': alert.message,
        'is_acknowledged': alert.is_acknowledged
    } for alert in alerts]
    
    return jsonify(alerts_data)


@app.route('/api/transport/buses/<int:bus_id>/driver', methods=['POST'])
@login_required
@role_required('TransportManager', 'SchoolAdmin', 'SuperAdmin')
def assign_driver(bus_id):
    """Assign driver to a bus"""
    try:
        bus = Bus.query.filter_by(id=bus_id, school_id=current_user.school_id).first()
        if not bus:
            return jsonify({'error': 'Bus not found'}), 404
        
        data = request.get_json()
        driver_id = data.get('driver_id')
        
        from models import Role, roles_users, User
        # Verify the user is a driver
        driver = User.query.join(roles_users).join(Role).filter(
            User.id == driver_id,
            User.school_id == current_user.school_id,
            Role.name == 'Driver'
        ).first()
        
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        bus.driver_id = driver_id
        db.session.commit()
        
        return jsonify({'message': 'Driver assigned successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error assigning driver: {e}")
        return jsonify({'error': 'Failed to assign driver'}), 500

@app.route('/api/transport/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    alert = Alert.query.join(Bus).filter(
        Alert.id == alert_id,
        Bus.school_id == current_user.school_id
    ).first()
    
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Alert acknowledged successfully'})

def check_alerts(telemetry, bus):
    """Check for various alert conditions"""
    alerts_to_create = []
    
    # Speed limit alert (assuming 80 km/h as limit)
    if telemetry.speed_kmh > 80:
        alert = Alert()
        alert.bus_id = bus.id
        alert.level = 'WARNING'
        alert.title = 'Speed Limit Exceeded'
        alert.message = f'Bus {bus.name} is traveling at {telemetry.speed_kmh:.1f} km/h'
        alerts_to_create.append(alert)
    
    # Low fuel alert
    fuel_percentage = (telemetry.fuel_level_liters / bus.fuel_tank_capacity) * 100
    if fuel_percentage < 20:
        level = 'CRITICAL' if fuel_percentage < 10 else 'WARNING'
        alert = Alert()
        alert.bus_id = bus.id
        alert.level = level
        alert.title = 'Low Fuel Level'
        alert.message = f'Bus {bus.name} fuel level is at {fuel_percentage:.1f}%'
        alerts_to_create.append(alert)
    
    # Engine idle alert (speed is 0 but engine is on for extended period)
    if telemetry.speed_kmh == 0 and telemetry.engine_on:
        # Check if bus has been idle for more than 10 minutes
        recent_telemetry = Telemetry.query.filter_by(bus_id=bus.id).filter(
            Telemetry.timestamp >= datetime.utcnow() - timedelta(minutes=10)
        ).all()
        
        if len(recent_telemetry) > 5 and all(t.speed_kmh == 0 and t.engine_on for t in recent_telemetry[-5:]):
            alert = Alert()
            alert.bus_id = bus.id
            alert.level = 'INFO'
            alert.title = 'Extended Idling Detected'
            alert.message = f'Bus {bus.name} has been idling for more than 10 minutes'
            alerts_to_create.append(alert)
    
    # Add alerts to database
    for alert in alerts_to_create:
        db.session.add(alert)

# SocketIO event handlers
@socketio.on('join_transport_room')
def on_join_transport_room(data):
    if current_user.is_authenticated:
        room = f'school_{current_user.school_id}'
        from flask_socketio import join_room
        join_room(room)
        emit('joined_transport_room', {'room': room})

@socketio.on('leave_transport_room')
def on_leave_transport_room(data):
    if current_user.is_authenticated:
        room = f'school_{current_user.school_id}'
        from flask_socketio import leave_room
        leave_room(room)
        emit('left_transport_room', {'room': room})
