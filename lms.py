from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import app, db
from models import Course, Assignment, Submission, Enrollment, Attendance, ClassRoom, User, Role
from utils import role_required
from datetime import datetime, date

@app.route('/lms')
@login_required
def lms_dashboard():
    user_role = current_user.get_primary_role()
    
    if user_role == 'Teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        recent_submissions = Submission.query.join(Assignment).join(Course).filter(
            Course.teacher_id == current_user.id
        ).order_by(Submission.submitted_at.desc()).limit(10).all()
        
        return render_template('lms.html', 
                             courses=courses, 
                             submissions=recent_submissions,
                             user_role=user_role)
    
    elif user_role == 'Student':
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        courses = [enrollment.course for enrollment in enrollments]
        pending_assignments = Assignment.query.join(Course).join(Enrollment).filter(
            Enrollment.student_id == current_user.id,
            Assignment.due_date > datetime.utcnow()
        ).order_by(Assignment.due_date).all()
        
        return render_template('lms.html', 
                             courses=courses, 
                             assignments=pending_assignments,
                             user_role=user_role)
    
    elif user_role in ['SchoolAdmin', 'SuperAdmin']:
        total_courses = Course.query.filter_by(school_id=current_user.school_id).count()
        from models import roles_users
        total_students = User.query.join(roles_users).join(Role).filter(
            User.school_id == current_user.school_id,
            Role.name == 'Student'
        ).count()
        total_teachers = User.query.join(roles_users).join(Role).filter(
            User.school_id == current_user.school_id,
            Role.name == 'Teacher'
        ).count()
        
        return render_template('lms.html',
                             total_courses=total_courses,
                             total_students=total_students,
                             total_teachers=total_teachers,
                             user_role=user_role)
    
    return render_template('lms.html', user_role=user_role)

@app.route('/api/lms/courses')
@login_required
def get_courses():
    user_role = current_user.get_primary_role()
    
    if user_role == 'Teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    elif user_role == 'Student':
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        courses = [enrollment.course for enrollment in enrollments]
    elif user_role in ['SchoolAdmin', 'SuperAdmin']:
        courses = Course.query.filter_by(school_id=current_user.school_id).all()
    else:
        courses = []
    
    courses_data = []
    for course in courses:
        course_data = {
            'id': course.id,
            'name': course.name,
            'description': course.description,
            'teacher_name': course.teacher.full_name if course.teacher else 'Not Assigned',
            'classroom_name': course.classroom.name if course.classroom else None,
            'enrolled_students': len(course.enrollments),
            'assignments_count': len(course.assignments)
        }
        courses_data.append(course_data)
    
    return jsonify(courses_data)

@app.route('/api/lms/courses', methods=['POST'])
@login_required
@role_required('Teacher', 'SchoolAdmin', 'SuperAdmin')
def create_course():
    data = request.get_json()
    
    course = Course()
    course.school_id = current_user.school_id
    course.name = data.get('name')
    course.description = data.get('description')
    course.teacher_id = current_user.id if current_user.has_role('Teacher') else data.get('teacher_id')
    course.classroom_id = data.get('classroom_id')
    
    db.session.add(course)
    db.session.commit()
    
    return jsonify({'message': 'Course created successfully', 'course_id': course.id}), 201

@app.route('/api/lms/courses/<int:course_id>/assignments')
@login_required
def get_assignments(course_id):
    # Verify user has access to this course
    course = Course.query.filter_by(id=course_id, school_id=current_user.school_id).first()
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    user_role = current_user.get_primary_role()
    if user_role == 'Student':
        # Check if student is enrolled
        enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
        if not enrollment:
            return jsonify({'error': 'Not enrolled in this course'}), 403
    elif user_role == 'Teacher' and course.teacher_id != current_user.id:
        return jsonify({'error': 'Not authorized for this course'}), 403
    
    assignments = Assignment.query.filter_by(course_id=course_id).order_by(Assignment.due_date).all()
    
    assignments_data = []
    for assignment in assignments:
        assignment_data = {
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
            'max_grade': assignment.max_grade,
            'created_at': assignment.created_at.isoformat()
        }
        
        # Add submission info for students
        if user_role == 'Student':
            submission = Submission.query.filter_by(
                assignment_id=assignment.id, 
                student_id=current_user.id
            ).first()
            assignment_data['submitted'] = submission is not None
            if submission:
                assignment_data['submission'] = {
                    'submitted_at': submission.submitted_at.isoformat(),
                    'grade': submission.grade,
                    'feedback': submission.feedback
                }
        
        assignments_data.append(assignment_data)
    
    return jsonify(assignments_data)

@app.route('/api/lms/assignments', methods=['POST'])
@login_required
@role_required('Teacher', 'SchoolAdmin', 'SuperAdmin')
def create_assignment():
    data = request.get_json()
    course_id = data.get('course_id')
    
    # Verify teacher has access to this course
    course = Course.query.filter_by(id=course_id, school_id=current_user.school_id).first()
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if current_user.has_role('Teacher') and course.teacher_id != current_user.id:
        return jsonify({'error': 'Not authorized for this course'}), 403
    
    assignment = Assignment()
    assignment.course_id = course_id
    assignment.title = data.get('title')
    assignment.description = data.get('description')
    assignment.due_date = datetime.fromisoformat(data.get('due_date')) if data.get('due_date') else None
    assignment.max_grade = data.get('max_grade', 100.0)
    
    db.session.add(assignment)
    db.session.commit()
    
    return jsonify({'message': 'Assignment created successfully', 'assignment_id': assignment.id}), 201

@app.route('/api/lms/assignments/<int:assignment_id>/submit', methods=['POST'])
@login_required
@role_required('Student')
def submit_assignment(assignment_id):
    assignment = Assignment.query.join(Course).filter(
        Assignment.id == assignment_id,
        Course.school_id == current_user.school_id
    ).first()
    
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404
    
    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id, 
        course_id=assignment.course_id
    ).first()
    if not enrollment:
        return jsonify({'error': 'Not enrolled in this course'}), 403
    
    # Check if already submitted
    existing_submission = Submission.query.filter_by(
        assignment_id=assignment_id,
        student_id=current_user.id
    ).first()
    
    data = request.get_json()
    
    if existing_submission:
        # Update existing submission
        existing_submission.content = data.get('content')
        existing_submission.submitted_at = datetime.utcnow()
        submission = existing_submission
    else:
        # Create new submission
        submission = Submission()
        submission.assignment_id = assignment_id
        submission.student_id = current_user.id
        submission.content = data.get('content')
        db.session.add(submission)
    
    db.session.commit()
    
    return jsonify({'message': 'Assignment submitted successfully', 'submission_id': submission.id}), 201

@app.route('/api/lms/submissions/<int:submission_id>/grade', methods=['POST'])
@login_required
@role_required('Teacher', 'SchoolAdmin', 'SuperAdmin')
def grade_submission(submission_id):
    submission = Submission.query.join(Assignment).join(Course).filter(
        Submission.id == submission_id,
        Course.school_id == current_user.school_id
    ).first()
    
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    # Check if teacher has access to this course
    if current_user.has_role('Teacher') and submission.assignment.course.teacher_id != current_user.id:
        return jsonify({'error': 'Not authorized for this course'}), 403
    
    data = request.get_json()
    
    submission.grade = data.get('grade')
    submission.feedback = data.get('feedback')
    
    db.session.commit()
    
    return jsonify({'message': 'Submission graded successfully'})

@app.route('/api/lms/attendance')
@login_required
def get_attendance():
    date_str = request.args.get('date', date.today().isoformat())
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    user_role = current_user.get_primary_role()
    
    if user_role == 'Teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        attendance_data = []
        
        for course in courses:
            enrollments = Enrollment.query.filter_by(course_id=course.id).all()
            course_attendance = []
            
            for enrollment in enrollments:
                attendance_record = Attendance.query.filter_by(
                    course_id=course.id,
                    student_id=enrollment.student_id,
                    date=target_date
                ).first()
                
                course_attendance.append({
                    'student_id': enrollment.student_id,
                    'student_name': enrollment.student.full_name,
                    'present': attendance_record.present if attendance_record else False,
                    'notes': attendance_record.notes if attendance_record else ''
                })
            
            attendance_data.append({
                'course_id': course.id,
                'course_name': course.name,
                'attendance': course_attendance
            })
        
        return jsonify(attendance_data)
    
    elif user_role == 'Student':
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        attendance_data = []
        
        for enrollment in enrollments:
            attendance_record = Attendance.query.filter_by(
                course_id=enrollment.course_id,
                student_id=current_user.id,
                date=target_date
            ).first()
            
            attendance_data.append({
                'course_id': enrollment.course_id,
                'course_name': enrollment.course.name,
                'present': attendance_record.present if attendance_record else False,
                'notes': attendance_record.notes if attendance_record else ''
            })
        
        return jsonify(attendance_data)
    
    return jsonify({'error': 'Unauthorized'}), 403

@app.route('/api/lms/attendance', methods=['POST'])
@login_required
@role_required('Teacher', 'SchoolAdmin', 'SuperAdmin')
def mark_attendance():
    data = request.get_json()
    course_id = data.get('course_id')
    date_str = data.get('date', date.today().isoformat())
    attendance_records = data.get('attendance', [])
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Verify course access
    course = Course.query.filter_by(id=course_id, school_id=current_user.school_id).first()
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if current_user.has_role('Teacher') and course.teacher_id != current_user.id:
        return jsonify({'error': 'Not authorized for this course'}), 403
    
    # Update attendance records
    for record in attendance_records:
        student_id = record.get('student_id')
        present = record.get('present', False)
        notes = record.get('notes', '')
        
        # Check if attendance record already exists
        existing_attendance = Attendance.query.filter_by(
            course_id=course_id,
            student_id=student_id,
            date=target_date
        ).first()
        
        if existing_attendance:
            existing_attendance.present = present
            existing_attendance.notes = notes
        else:
            new_attendance = Attendance()
            new_attendance.course_id = course_id
            new_attendance.student_id = student_id
            new_attendance.date = target_date
            new_attendance.present = present
            new_attendance.notes = notes
            db.session.add(new_attendance)
    
    db.session.commit()
    
    return jsonify({'message': 'Attendance marked successfully'})

@app.route('/api/lms/enroll', methods=['POST'])
@login_required
@role_required('Student', 'SchoolAdmin', 'SuperAdmin')
def enroll_course():
    data = request.get_json()
    course_id = data.get('course_id')
    student_id = data.get('student_id', current_user.id)
    
    # Verify course exists and belongs to school
    course = Course.query.filter_by(id=course_id, school_id=current_user.school_id).first()
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        course_id=course_id
    ).first()
    
    if existing_enrollment:
        return jsonify({'error': 'Already enrolled in this course'}), 400
    
    # Create enrollment
    enrollment = Enrollment()
    enrollment.student_id = student_id
    enrollment.course_id = course_id
    
    db.session.add(enrollment)
    db.session.commit()
    
    return jsonify({'message': 'Enrolled successfully'}), 201
