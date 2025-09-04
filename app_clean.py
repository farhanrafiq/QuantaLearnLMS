import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()
scheduler = BackgroundScheduler()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "quantafons-dev-secret-key-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database with better error handling
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # For development only
    database_url = "sqlite:///quantafons_lms.db"
    logging.warning("No DATABASE_URL found, using SQLite for development")
else:
    logging.info(f"Using database: {database_url[:20]}...")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
socketio.init_app(app, async_mode='threading')
migrate.init_app(app, db)

# Import all modules
from auth import *
from lms import *
from transport import *
from settings import *
from utils import *
from models import *

# Initialize MQTT and scheduler if available
try:
    from mqtt_client import init_mqtt_client
    init_mqtt_client()
except Exception as e:
    logging.warning(f"MQTT client not available: {e}")

try:
    from utils import init_scheduler
    init_scheduler()
except Exception as e:
    logging.warning(f"Scheduler not available: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)