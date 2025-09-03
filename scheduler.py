from datetime import datetime, timedelta
import logging
from app import db

def init_scheduler(scheduler, app):
    """Initialize scheduled jobs"""
    
    def cleanup_old_telemetry():
        """Clean up old telemetry data (keep only last 90 days)"""
        with app.app_context():
            try:
                from models import Telemetry
                cutoff_date = datetime.utcnow() - timedelta(days=90)
                old_records = Telemetry.query.filter(Telemetry.timestamp < cutoff_date).delete()
                db.session.commit()
                if old_records > 0:
                    logging.info(f"Cleaned up {old_records} old telemetry records")
            except Exception as e:
                logging.error(f"Error cleaning up telemetry data: {e}")
                db.session.rollback()
    
    def check_bus_offline():
        """Check for buses that haven't sent telemetry in a while"""
        with app.app_context():
            try:
                from models import Bus, Telemetry, Alert
                
                # Get all active buses
                buses = Bus.query.filter_by(is_active=True).all()
                
                for bus in buses:
                    # Get latest telemetry
                    latest_telemetry = Telemetry.query.filter_by(bus_id=bus.id).order_by(
                        Telemetry.timestamp.desc()
                    ).first()
                    
                    if latest_telemetry:
                        time_since_last = datetime.utcnow() - latest_telemetry.timestamp
                        
                        # If no data for more than 1 hour, create alert
                        if time_since_last > timedelta(hours=1):
                            # Check if alert already exists
                            existing_alert = Alert.query.filter_by(
                                bus_id=bus.id,
                                title='Bus Offline',
                                is_acknowledged=False
                            ).first()
                            
                            if not existing_alert:
                                alert = Alert()
                                alert.bus_id = bus.id
                                alert.level = 'WARNING'
                                alert.title = 'Bus Offline'
                                alert.message = f'Bus {bus.name} has not transmitted data for {time_since_last}'
                                db.session.add(alert)
                
                db.session.commit()
                
            except Exception as e:
                logging.error(f"Error checking offline buses: {e}")
                db.session.rollback()
    
    def generate_daily_fuel_report():
        """Generate daily fuel consumption reports"""
        with app.app_context():
            try:
                from models import Bus, Telemetry, FuelEvent
                from utils import calculate_fuel_efficiency
                
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                start_time = datetime.combine(yesterday, datetime.min.time())
                end_time = datetime.combine(yesterday, datetime.max.time())
                
                buses = Bus.query.filter_by(is_active=True).all()
                
                for bus in buses:
                    # Get telemetry for yesterday
                    telemetry_data = Telemetry.query.filter(
                        Telemetry.bus_id == bus.id,
                        Telemetry.timestamp >= start_time,
                        Telemetry.timestamp <= end_time
                    ).order_by(Telemetry.timestamp).all()
                    
                    if len(telemetry_data) > 1:
                        efficiency = calculate_fuel_efficiency(telemetry_data)
                        
                        # Create fuel event for daily summary
                        if efficiency.get('total_fuel_consumed_l', 0) > 0:
                            fuel_event = FuelEvent()
                            fuel_event.bus_id = bus.id
                            fuel_event.timestamp = end_time
                            fuel_event.event_type = 'DAILY_SUMMARY'
                            fuel_event.amount_liters = efficiency['total_fuel_consumed_l']
                            fuel_event.details = f"Daily consumption: {efficiency['total_fuel_consumed_l']:.1f}L, " \
                                               f"Distance: {efficiency['total_distance_km']:.1f}km, " \
                                               f"Efficiency: {efficiency['overall_kmpl']:.1f} km/L"
                            fuel_event.severity = 'INFO'
                            db.session.add(fuel_event)
                
                db.session.commit()
                logging.info("Daily fuel reports generated")
                
            except Exception as e:
                logging.error(f"Error generating daily fuel reports: {e}")
                db.session.rollback()
    
    def send_attendance_reminder():
        """Send attendance reminder to teachers"""
        with app.app_context():
            try:
                from models import User, Course
                
                # Get all teachers
                from models import Role, roles_users
                teachers = User.query.join(roles_users).join(Role).filter(
                    Role.name == 'Teacher',
                    User.active == True
                ).all()
                
                today = datetime.utcnow().date()
                
                for teacher in teachers:
                    courses_today = Course.query.filter_by(teacher_id=teacher.id).all()
                    
                    if courses_today:
                        # In a real application, you would send email/SMS here
                        logging.info(f"Attendance reminder for teacher {teacher.full_name}")
                
            except Exception as e:
                logging.error(f"Error sending attendance reminders: {e}")
    
    # Add jobs to scheduler
    scheduler.add_job(cleanup_old_telemetry, 'interval', minutes=30, id='cleanup_old_telemetry')
    scheduler.add_job(check_bus_offline, 'interval', minutes=10, id='check_bus_offline')
    scheduler.add_job(generate_daily_fuel_report, 'cron', hour=0, minute=0, id='daily_fuel_report')
    scheduler.add_job(send_attendance_reminder, 'cron', hour=6, minute=0, id='morning_attendance_reminder')
    
    logging.info("Scheduler jobs initialized")
