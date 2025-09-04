import os
import json
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
from app_final import db

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER_URL', 'broker.hivemq.com')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'quantafons/+/buses/+/telemetry')

def on_connect(client, userdata, flags, rc):
    """Callback for when the client receives a CONNACK response from the server"""
    if rc == 0:
        logging.info("Connected to MQTT broker successfully")
        client.subscribe(MQTT_TOPIC)
        logging.info(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        logging.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    """Callback for when a PUBLISH message is received from the server"""
    try:
        # Parse topic to extract school_id and bus_id
        # Expected format: quantafons/{school_id}/buses/{bus_id}/telemetry
        topic_parts = msg.topic.split('/')
        if len(topic_parts) >= 5:
            school_id = topic_parts[1]
            bus_id = topic_parts[3]
            
            # Parse message payload
            payload = json.loads(msg.payload.decode())
            
            # Get Flask app context
            app = userdata['app']
            with app.app_context():
                from models import Bus, Telemetry, FuelEvent, Alert
                from utils import detect_fuel_anomaly
                
                # Verify bus exists and belongs to school
                bus = Bus.query.filter_by(id=bus_id).first()
                if not bus or str(bus.school_id) != school_id:
                    logging.warning(f"Invalid bus_id {bus_id} for school {school_id}")
                    return
                
                # Create telemetry record
                telemetry = Telemetry()
                telemetry.bus_id = bus_id
                telemetry.latitude = payload.get('latitude')
                telemetry.longitude = payload.get('longitude')
                telemetry.speed_kmh = payload.get('speed_kmh', 0)
                telemetry.fuel_level_liters = payload.get('fuel_level_liters')
                telemetry.fuel_flow_lph = payload.get('fuel_flow_lph', 0)
                telemetry.odometer_km = payload.get('odometer_km', 0)
                telemetry.engine_on = payload.get('engine_on', False)
                telemetry.heading = payload.get('heading')
                telemetry.altitude = payload.get('altitude')
                
                db.session.add(telemetry)
                
                # Analyze for fuel anomalies
                previous_telemetry = Telemetry.query.filter_by(bus_id=bus_id).order_by(
                    Telemetry.timestamp.desc()
                ).offset(1).first()
                
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
                
                db.session.commit()
                
                # Emit SocketIO update
                from app_final import socketio
                socketio.emit('telemetry_update', {
                    'bus_id': int(bus_id),
                    'latitude': telemetry.latitude,
                    'longitude': telemetry.longitude,
                    'speed_kmh': telemetry.speed_kmh,
                    'fuel_level_liters': telemetry.fuel_level_liters,
                    'engine_on': telemetry.engine_on,
                    'timestamp': telemetry.timestamp.isoformat()
                }, to=f'school_{school_id}')
                
                logging.info(f"Processed MQTT telemetry for bus {bus_id}")
                
    except Exception as e:
        logging.error(f"Error processing MQTT message: {e}")

def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the server"""
    if rc != 0:
        logging.warning("Unexpected MQTT disconnection. Will auto-reconnect")

def init_mqtt(app):
    """Initialize MQTT client"""
    try:
        client = mqtt.Client()
        client.user_data_set({'app': app})
        
        # Set callbacks
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        # Set credentials if provided
        if MQTT_USERNAME and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        # Connect to broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start the loop in a separate thread
        client.loop_start()
        
        logging.info("MQTT client initialized and connected")
        
    except Exception as e:
        logging.error(f"Failed to initialize MQTT client: {e}")
