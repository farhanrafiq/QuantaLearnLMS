from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from app import app, db
from models import User, Role, School

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
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact administrator.', 'error')
                return render_template('login.html')
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        school_name = data.get('school_name', 'Default School')
        role_name = data.get('role', 'Student')
        
        if not all([email, password, full_name]):
            if request.is_json:
                return jsonify({'error': 'Email, password, and full name are required'}), 400
            flash('Email, password, and full name are required.', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'error': 'Email already registered'}), 400
            flash('Email already registered.', 'error')
            return render_template('register.html')
        
        # Get or create school
        school = School.query.filter_by(name=school_name).first()
        if not school:
            school = School()
            school.name = school_name
            db.session.add(school)
            db.session.commit()
        
        # Get role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role.query.filter_by(name='Student').first()
        
        # Create user
        user = User()
        user.email = email
        user.password_hash = generate_password_hash(password)
        user.full_name = full_name
        user.school_id = school.id
        user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'message': 'User registered successfully'}), 201
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_role = current_user.get_primary_role()
    current_date = datetime.now().strftime('%B %d, %Y')
    return render_template('dashboard.html', user_role=user_role, current_date=current_date)

# API Endpoints for mobile/external access
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        if not user.is_active:
            return jsonify({'error': 'Account deactivated'}), 403
        
        # For API, we'll use a simple token (in production, use JWT)
        token = f"user_{user.id}_token"
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.get_primary_role(),
                'school_id': user.school_id
            }
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/profile')
@login_required
def api_profile():
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'role': current_user.get_primary_role(),
        'school_id': current_user.school_id,
        'school_name': current_user.school.name
    })
