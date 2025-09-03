# Overview

QuantaFONS is a comprehensive Flask-based Learning Management System (LMS) designed for schools with a flagship Transport Management module. The application supports multi-tenant architecture where each school operates independently with role-based access control including SuperAdmin, SchoolAdmin, Teacher, Student, Parent, TransportManager, Driver, and Accountant roles.

The system features a complete LMS with courses, assignments, and submissions, alongside a sophisticated transport management system that provides real-time GPS tracking of school buses, fuel monitoring through sensor integration, route planning with waypoints, and comprehensive analytics for fuel consumption and efficiency metrics.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM for database operations
- **Database**: SQLite for development, PostgreSQL for production with Flask-Migrate for schema management
- **Authentication**: Dual authentication system using Flask-Login for web sessions and Flask-JWT-Extended for API token authentication
- **Real-time Communication**: Flask-SocketIO with eventlet for live bus tracking and notifications
- **Background Processing**: APScheduler for periodic tasks like telemetry cleanup and offline bus detection
- **Multi-tenancy**: School-based data isolation with foreign key relationships

## Frontend Architecture
- **Technology Stack**: Vanilla JavaScript ES6 modules with Bootstrap 5 for responsive design
- **Real-time Updates**: Socket.IO client for live transport tracking and system notifications
- **Mapping**: Leaflet.js via CDN for interactive maps and geospatial visualizations
- **State Management**: Module-based JavaScript architecture with dedicated managers for Dashboard, LMS, and Transport features
- **UI Components**: Custom CSS with CSS variables for consistent theming and responsive modals

## Data Storage Solutions
- **Primary Database**: SQLAlchemy with declarative base for object-relational mapping
- **Schema Design**: Normalized database with proper foreign key relationships and association tables for many-to-many relationships
- **Multi-tenant Architecture**: School-based data segregation ensuring data isolation between institutions
- **Migration Management**: Flask-Migrate for version-controlled database schema changes

## Authentication and Authorization
- **Role-based Access Control**: Eight distinct roles with hierarchical permissions (SuperAdmin > SchoolAdmin > functional roles)
- **Session Management**: Flask-Login for web-based authentication with remember-me functionality
- **API Security**: JWT tokens for API access with configurable expiration
- **Permission Decorators**: Custom role_required decorator for endpoint-level access control
- **Password Security**: Werkzeug password hashing with salt for secure credential storage

## Real-time Communication Architecture
- **Transport Tracking**: Socket.IO integration for live bus location updates and status changes
- **Event Broadcasting**: Room-based socket communication for school-specific updates
- **MQTT Integration**: Optional paho-mqtt client for receiving telemetry data from IoT devices
- **Background Scheduling**: APScheduler for automated tasks like telemetry cleanup and alert generation

# External Dependencies

## Core Framework Dependencies
- **Flask Ecosystem**: Flask 3.0.3, Flask-SQLAlchemy 3.1.1, Flask-Login 0.6.3, Flask-SocketIO 5.3.6
- **Database**: psycopg2-binary for PostgreSQL connectivity, Flask-Migrate for schema management
- **Authentication**: Flask-JWT-Extended for API token management, Werkzeug for password hashing
- **Configuration**: python-dotenv for environment variable management

## Real-time and Communication
- **WebSocket Support**: eventlet WSGI server for Socket.IO compatibility
- **IoT Integration**: paho-mqtt client for receiving telemetry data from GPS and fuel monitoring devices
- **Background Processing**: APScheduler for periodic job execution and system maintenance

## Frontend CDN Dependencies
- **UI Framework**: Bootstrap 5.3.0 via CDN for responsive design components
- **Icons**: Font Awesome 6.4.0 for consistent iconography
- **Mapping**: Leaflet 1.9.4 for interactive maps and geospatial features
- **Real-time**: Socket.IO client via CDN for WebSocket communication

## Optional Integrations
- **Payment Processing**: Razorpay integration for fee management (configurable)
- **Geospatial Analysis**: haversine library for distance calculations and route optimization
- **MQTT Broker**: Configurable MQTT broker connection (defaults to HiveMQ public broker)
- **CORS Support**: Flask-CORS for cross-origin request handling in distributed deployments

## Development and Production Tools
- **Database Migration**: Flask-Migrate for version-controlled schema changes
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies
- **Environment Configuration**: Flexible configuration through environment variables with sensible defaults
- **Logging**: Python logging module with configurable levels for debugging and monitoring