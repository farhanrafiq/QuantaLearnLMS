// QuantaFONS Learning Management System Module
// Handles courses, assignments, submissions, attendance, and grading

const LMSManager = {
    userRole: null,
    currentCourseId: null,
    charts: {},
    refreshInterval: null,
    socket: null,

    init(role) {
        this.userRole = role;
        console.log(`Initializing LMS Manager for role: ${role}`);
        
        this.setupEventListeners();
        this.loadInitialData();
        this.setupAutoRefresh();
        this.initializeCharts();
    },

    setupEventListeners() {
        // Course selection handlers
        document.addEventListener('click', (e) => {
            if (e.target.closest('.course-card')) {
                const courseId = e.target.closest('.course-card').dataset.courseId;
                if (courseId) {
                    this.selectCourse(parseInt(courseId));
                }
            }

            if (e.target.matches('[data-action="refresh-courses"]')) {
                this.loadCourses();
            }

            if (e.target.matches('[data-action="refresh-assignments"]')) {
                this.loadAssignments();
            }
        });

        // Form submissions
        this.setupFormHandlers();
    },

    setupFormHandlers() {
        // Course creation form
        const createCourseForm = document.getElementById('createCourseForm');
        if (createCourseForm) {
            createCourseForm.addEventListener('submit', this.handleCourseCreation.bind(this));
        }

        // Assignment creation form
        const createAssignmentForm = document.getElementById('createAssignmentForm');
        if (createAssignmentForm) {
            createAssignmentForm.addEventListener('submit', this.handleAssignmentCreation.bind(this));
        }

        // Assignment submission form
        const submitAssignmentForm = document.getElementById('submitAssignmentForm');
        if (submitAssignmentForm) {
            submitAssignmentForm.addEventListener('submit', this.handleAssignmentSubmission.bind(this));
        }

        // Attendance form
        const attendanceForm = document.getElementById('attendanceForm');
        if (attendanceForm) {
            attendanceForm.addEventListener('submit', this.handleAttendanceSubmission.bind(this));
        }
    },

    setupAutoRefresh() {
        // Refresh data every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.loadInitialData();
        }, 300000);
    },

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadCourses(),
                this.loadStats()
            ]);

            // Load role-specific data
            if (this.userRole === 'Teacher') {
                await this.loadTeacherData();
            } else if (this.userRole === 'Student') {
                await this.loadStudentData();
            }

        } catch (error) {
            console.error('Error loading initial LMS data:', error);
            window.QuantaFONS.Utils.showToast('Failed to load LMS data', 'error');
        }
    },

    async loadCourses() {
        try {
            const courses = await window.QuantaFONS.API.get('/lms/courses');
            this.renderCourses(courses);
            return courses;
        } catch (error) {
            console.error('Error loading courses:', error);
            this.showCoursesError();
            throw error;
        }
    },

    renderCourses(courses) {
        const containers = {
            teacherCoursesContent: document.getElementById('teacherCoursesContent'),
            studentCoursesContent: document.getElementById('studentCoursesContent'),
            allCoursesContent: document.getElementById('allCoursesContent')
        };

        Object.entries(containers).forEach(([key, element]) => {
            if (element) {
                this.renderCoursesInContainer(courses, element, key);
            }
        });
    },

    renderCoursesInContainer(courses, element, containerType) {
        if (!courses || courses.length === 0) {
            window.QuantaFONS.LoadingManager.empty(element, 'No courses available');
            return;
        }

        const coursesHTML = courses.map(course => `
            <div class="course-card mb-3" data-course-id="${course.id}">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <h5 class="card-title mb-2">${course.name}</h5>
                                <p class="card-text text-muted">${course.description || 'No description available'}</p>
                                <div class="course-meta">
                                    <small class="text-muted">
                                        ${containerType !== 'teacherCoursesContent' ? 
                                            `<i class="fas fa-user me-1"></i>${course.teacher_name || 'No teacher assigned'}` : 
                                            `<i class="fas fa-users me-1"></i>${course.enrolled_students || 0} students`
                                        }
                                        <i class="fas fa-tasks ms-3 me-1"></i>${course.assignments_count || 0} assignments
                                        ${course.classroom_name ? `<i class="fas fa-door-open ms-3 me-1"></i>${course.classroom_name}` : ''}
                                    </small>
                                </div>
                            </div>
                            <div class="course-actions">
                                <div class="dropdown">
                                    <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                        <i class="fas fa-ellipsis-v"></i>
                                    </button>
                                    <ul class="dropdown-menu">
                                        <li><a class="dropdown-item" href="#" onclick="LMSManager.viewCourse(${course.id})">
                                            <i class="fas fa-eye me-2"></i>View Course
                                        </a></li>
                                        ${this.userRole === 'Teacher' || this.userRole === 'SchoolAdmin' || this.userRole === 'SuperAdmin' ? `
                                            <li><a class="dropdown-item" href="#" onclick="LMSManager.editCourse(${course.id})">
                                                <i class="fas fa-edit me-2"></i>Edit Course
                                            </a></li>
                                            <li><a class="dropdown-item" href="#" onclick="LMSManager.manageEnrollments(${course.id})">
                                                <i class="fas fa-users me-2"></i>Manage Students
                                            </a></li>
                                        ` : ''}
                                        ${this.userRole === 'Student' ? `
                                            <li><a class="dropdown-item" href="#" onclick="LMSManager.viewAssignments(${course.id})">
                                                <i class="fas fa-tasks me-2"></i>View Assignments
                                            </a></li>
                                        ` : ''}
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Progress bar for students -->
                        ${this.userRole === 'Student' ? this.renderCourseProgress(course) : ''}
                        
                        <!-- Quick actions -->
                        <div class="course-quick-actions mt-3">
                            <div class="btn-group btn-group-sm w-100" role="group">
                                <button type="button" class="btn btn-outline-primary" onclick="LMSManager.viewCourse(${course.id})">
                                    <i class="fas fa-book-open me-1"></i>Enter Course
                                </button>
                                ${this.userRole === 'Teacher' ? `
                                    <button type="button" class="btn btn-outline-success" onclick="LMSManager.showCreateAssignment(${course.id})">
                                        <i class="fas fa-plus me-1"></i>Assignment
                                    </button>
                                    <button type="button" class="btn btn-outline-info" onclick="LMSManager.showAttendance(${course.id})">
                                        <i class="fas fa-user-check me-1"></i>Attendance
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        element.innerHTML = coursesHTML;
    },

    renderCourseProgress(course) {
        // This would typically calculate actual progress based on completed assignments
        const progress = Math.floor(Math.random() * 100); // Placeholder
        const progressColor = progress > 75 ? 'success' : progress > 50 ? 'warning' : 'danger';

        return `
            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Progress</small>
                    <small class="text-muted">${progress}%</small>
                </div>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-${progressColor}" role="progressbar" 
                         style="width: ${progress}%" aria-valuenow="${progress}" 
                         aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
        `;
    },

    showCoursesError() {
        const containers = ['teacherCoursesContent', 'studentCoursesContent', 'allCoursesContent'];
        containers.forEach(containerId => {
            const element = document.getElementById(containerId);
            if (element) {
                window.QuantaFONS.LoadingManager.error(element, 'Failed to load courses');
            }
        });
    },

    async loadStats() {
        try {
            // Update role-specific statistics
            const courseCount = await this.updateCourseCount();
            
            if (this.userRole === 'Teacher') {
                await this.updateTeacherStats();
            } else if (this.userRole === 'Student') {
                await this.updateStudentStats();
            }
            
        } catch (error) {
            console.error('Error loading LMS stats:', error);
        }
    },

    async updateCourseCount() {
        try {
            const courses = await window.QuantaFONS.API.get('/lms/courses');
            const counts = {
                teacherCourseCount: document.getElementById('teacherCourseCount'),
                enrolledCourses: document.getElementById('enrolledCourses'),
                totalCourses: document.getElementById('totalCourses')
            };

            Object.entries(counts).forEach(([key, element]) => {
                if (element) {
                    element.textContent = courses.length;
                }
            });

            return courses.length;
        } catch (error) {
            console.error('Error updating course count:', error);
            return 0;
        }
    },

    async updateTeacherStats() {
        // Update teacher-specific statistics
        const elements = {
            totalStudents: document.getElementById('totalStudents'),
            pendingSubmissions: document.getElementById('pendingSubmissions'),
            totalAssignments: document.getElementById('totalAssignments')
        };

        // These would typically come from API calls
        // For now, showing placeholder values
        if (elements.totalStudents) elements.totalStudents.textContent = '0';
        if (elements.pendingSubmissions) elements.pendingSubmissions.textContent = '0';
        if (elements.totalAssignments) elements.totalAssignments.textContent = '0';
    },

    async updateStudentStats() {
        // Update student-specific statistics
        const elements = {
            pendingAssignments: document.getElementById('pendingAssignments'),
            completedAssignments: document.getElementById('completedAssignments'),
            averageGrade: document.getElementById('averageGrade')
        };

        if (elements.pendingAssignments) elements.pendingAssignments.textContent = '0';
        if (elements.completedAssignments) elements.completedAssignments.textContent = '0';
        if (elements.averageGrade) elements.averageGrade.textContent = '--';
    },

    async loadTeacherData() {
        try {
            await this.loadRecentSubmissions();
            await this.loadAttendanceOverview();
        } catch (error) {
            console.error('Error loading teacher data:', error);
        }
    },

    async loadStudentData() {
        try {
            await this.loadUpcomingAssignments();
            await this.loadGradeSummary();
        } catch (error) {
            console.error('Error loading student data:', error);
        }
    },

    async loadRecentSubmissions() {
        const element = document.getElementById('recentSubmissions');
        if (!element) return;

        try {
            // This would typically fetch recent submissions for teacher's courses
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-clipboard-list fa-2x mb-2"></i>
                    <p>No recent submissions</p>
                </div>
            `;
        } catch (error) {
            window.QuantaFONS.LoadingManager.error(element, 'Failed to load submissions');
        }
    },

    async loadAttendanceOverview() {
        const element = document.getElementById('attendanceOverview');
        if (!element) return;

        try {
            // This would typically fetch today's attendance data
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-calendar-check fa-2x mb-2"></i>
                    <p>No attendance data for today</p>
                </div>
            `;
        } catch (error) {
            window.QuantaFONS.LoadingManager.error(element, 'Failed to load attendance data');
        }
    },

    async loadUpcomingAssignments() {
        const element = document.getElementById('upcomingAssignments');
        if (!element) return;

        try {
            // This would typically fetch upcoming assignments for student
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                    <p>No upcoming assignments</p>
                </div>
            `;
        } catch (error) {
            window.QuantaFONS.LoadingManager.error(element, 'Failed to load assignments');
        }
    },

    async loadGradeSummary() {
        const element = document.getElementById('gradeSummary');
        if (!element) return;

        try {
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-chart-line fa-2x mb-2"></i>
                    <p>Grade data will appear here</p>
                </div>
            `;
        } catch (error) {
            window.QuantaFONS.LoadingManager.error(element, 'Failed to load grades');
        }
    },

    selectCourse(courseId) {
        this.currentCourseId = courseId;
        console.log(`Selected course: ${courseId}`);
        
        // Update UI to show selected course
        document.querySelectorAll('.course-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedCard = document.querySelector(`[data-course-id="${courseId}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
    },

    viewCourse(courseId) {
        console.log(`Viewing course: ${courseId}`);
        // This would typically navigate to a detailed course view
        window.QuantaFONS.Utils.showToast('Course view coming soon!', 'info');
    },

    editCourse(courseId) {
        console.log(`Editing course: ${courseId}`);
        // This would typically open an edit modal
        window.QuantaFONS.Utils.showToast('Course editing coming soon!', 'info');
    },

    manageEnrollments(courseId) {
        console.log(`Managing enrollments for course: ${courseId}`);
        // This would typically open enrollment management
        window.QuantaFONS.Utils.showToast('Enrollment management coming soon!', 'info');
    },

    async viewAssignments(courseId) {
        try {
            const assignments = await window.QuantaFONS.API.get(`/lms/courses/${courseId}/assignments`);
            this.showAssignmentsModal(assignments, courseId);
        } catch (error) {
            console.error('Error loading assignments:', error);
            window.QuantaFONS.Utils.showToast('Failed to load assignments', 'error');
        }
    },

    showAssignmentsModal(assignments, courseId) {
        // Create and show assignments modal
        const modalHTML = `
            <div class="modal fade" id="assignmentsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-tasks me-2"></i>Course Assignments
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${this.renderAssignmentsList(assignments)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('assignmentsModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add new modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('assignmentsModal'));
        modal.show();
    },

    renderAssignmentsList(assignments) {
        if (!assignments || assignments.length === 0) {
            return `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-clipboard fa-2x mb-2"></i>
                    <p>No assignments available</p>
                </div>
            `;
        }

        return assignments.map(assignment => {
            const dueDate = assignment.due_date ? 
                window.QuantaFONS.Utils.formatDateTime(assignment.due_date) : 'No due date';
            const isOverdue = assignment.due_date && new Date(assignment.due_date) < new Date();
            const isSubmitted = assignment.submitted;

            return `
                <div class="assignment-item assignment-${isSubmitted ? 'completed' : isOverdue ? 'overdue' : 'due-soon'} p-3 mb-3 rounded">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${assignment.title}</h6>
                            <p class="mb-2 text-muted">${assignment.description || 'No description'}</p>
                            <div class="assignment-meta">
                                <small class="text-muted">
                                    <i class="fas fa-calendar me-1"></i>Due: ${dueDate}
                                    <i class="fas fa-star ms-3 me-1"></i>Max Grade: ${assignment.max_grade || 100}
                                    ${isSubmitted ? `<i class="fas fa-check ms-3 me-1 text-success"></i>Submitted` : ''}
                                </small>
                            </div>
                        </div>
                        <div class="assignment-actions">
                            ${!isSubmitted && !isOverdue ? `
                                <button class="btn btn-sm quantafons-btn-primary" onclick="LMSManager.submitAssignment(${assignment.id})">
                                    <i class="fas fa-paper-plane me-1"></i>Submit
                                </button>
                            ` : isSubmitted ? `
                                <span class="badge bg-success">
                                    <i class="fas fa-check me-1"></i>Submitted
                                </span>
                            ` : `
                                <span class="badge bg-danger">
                                    <i class="fas fa-exclamation-triangle me-1"></i>Overdue
                                </span>
                            `}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    showCreateAssignment(courseId) {
        this.currentCourseId = courseId;
        const modal = document.getElementById('createAssignmentModal');
        if (modal) {
            // Set course ID in form
            const courseIdField = modal.querySelector('[name="course_id"]');
            if (courseIdField) {
                courseIdField.value = courseId;
            }
            
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    },

    showAttendance(courseId) {
        this.currentCourseId = courseId;
        const modal = document.getElementById('attendanceModal');
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    },

    submitAssignment(assignmentId) {
        console.log(`Submitting assignment: ${assignmentId}`);
        // This would typically open a submission modal
        window.QuantaFONS.Utils.showToast('Assignment submission coming soon!', 'info');
    },

    async handleCourseCreation(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const courseData = Object.fromEntries(formData.entries());
        
        try {
            const result = await window.QuantaFONS.API.post('/lms/courses', courseData);
            
            window.QuantaFONS.Utils.showToast('Course created successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(event.target.closest('.modal'));
            if (modal) {
                modal.hide();
            }
            
            // Reset form
            event.target.reset();
            
            // Refresh courses
            this.loadCourses();
            
        } catch (error) {
            console.error('Error creating course:', error);
            window.QuantaFONS.Utils.showToast('Failed to create course: ' + error.message, 'error');
        }
    },

    async handleAssignmentCreation(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const assignmentData = Object.fromEntries(formData.entries());
        
        // Ensure course_id is set
        if (!assignmentData.course_id && this.currentCourseId) {
            assignmentData.course_id = this.currentCourseId;
        }
        
        try {
            const result = await window.QuantaFONS.API.post('/lms/assignments', assignmentData);
            
            window.QuantaFONS.Utils.showToast('Assignment created successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(event.target.closest('.modal'));
            if (modal) {
                modal.hide();
            }
            
            // Reset form
            event.target.reset();
            
        } catch (error) {
            console.error('Error creating assignment:', error);
            window.QuantaFONS.Utils.showToast('Failed to create assignment: ' + error.message, 'error');
        }
    },

    async handleAssignmentSubmission(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const submissionData = Object.fromEntries(formData.entries());
        const assignmentId = submissionData.assignment_id;
        
        try {
            const result = await window.QuantaFONS.API.post(`/lms/assignments/${assignmentId}/submit`, submissionData);
            
            window.QuantaFONS.Utils.showToast('Assignment submitted successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(event.target.closest('.modal'));
            if (modal) {
                modal.hide();
            }
            
            // Reset form
            event.target.reset();
            
        } catch (error) {
            console.error('Error submitting assignment:', error);
            window.QuantaFONS.Utils.showToast('Failed to submit assignment: ' + error.message, 'error');
        }
    },

    async handleAttendanceSubmission(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const attendanceData = Object.fromEntries(formData.entries());
        
        try {
            const result = await window.QuantaFONS.API.post('/lms/attendance', attendanceData);
            
            window.QuantaFONS.Utils.showToast('Attendance marked successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(event.target.closest('.modal'));
            if (modal) {
                modal.hide();
            }
            
            // Reset form
            event.target.reset();
            
        } catch (error) {
            console.error('Error marking attendance:', error);
            window.QuantaFONS.Utils.showToast('Failed to mark attendance: ' + error.message, 'error');
        }
    },

    initializeCharts() {
        // Initialize charts after a short delay to ensure DOM is ready
        setTimeout(() => {
            this.initializeAssignmentProgressChart();
            this.initializeEnrollmentTrendsChart();
            this.initializeGradeDistributionChart();
            this.initializeSystemStatsChart();
        }, 500);
    },

    initializeAssignmentProgressChart() {
        const ctx = document.getElementById('assignmentProgressChart');
        if (!ctx) return;

        if (this.charts.assignmentProgress) {
            this.charts.assignmentProgress.destroy();
        }

        // Sample data - this would come from API in real implementation
        this.charts.assignmentProgress = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'In Progress', 'Overdue'],
                datasets: [{
                    data: [65, 25, 10],
                    backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Assignment Progress'
                    }
                }
            }
        });
    },

    initializeEnrollmentTrendsChart() {
        const ctx = document.getElementById('enrollmentTrendsChart');
        if (!ctx) return;

        if (this.charts.enrollmentTrends) {
            this.charts.enrollmentTrends.destroy();
        }

        this.charts.enrollmentTrends = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'New Enrollments',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Enrollment Trends'
                    }
                }
            }
        });
    },

    initializeGradeDistributionChart() {
        const ctx = document.getElementById('gradeDistributionChart');
        if (!ctx) return;

        if (this.charts.gradeDistribution) {
            this.charts.gradeDistribution.destroy();
        }

        this.charts.gradeDistribution = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['A', 'B', 'C', 'D', 'F'],
                datasets: [{
                    label: 'Number of Students',
                    data: [23, 45, 32, 12, 5],
                    backgroundColor: ['#28a745', '#ffc107', '#17a2b8', '#fd7e14', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Grade Distribution'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    },

    initializeSystemStatsChart() {
        const ctx = document.getElementById('systemStatsChart');
        if (!ctx) return;

        if (this.charts.systemStats) {
            this.charts.systemStats.destroy();
        }

        this.charts.systemStats = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Courses', 'Students', 'Teachers', 'Assignments', 'Submissions'],
                datasets: [{
                    label: 'System Activity',
                    data: [80, 90, 70, 85, 75],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    pointBackgroundColor: '#2563eb'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'System Statistics'
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    },

    destroy() {
        // Clean up intervals
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Clean up socket listeners
        if (this.socket) {
            // Remove any LMS-specific socket listeners
        }

        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
};

// Add custom styles for course cards
const style = document.createElement('style');
style.textContent = `
    .course-card.selected .card {
        border-color: var(--quantafons-primary);
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
    }
    
    .course-card .card {
        transition: all 0.2s ease;
    }
    
    .course-card:hover .card {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .assignment-item {
        transition: all 0.2s ease;
    }
    
    .assignment-item:hover {
        transform: translateX(4px);
    }
`;
document.head.appendChild(style);

// Make LMSManager globally available
window.LMSManager = LMSManager;

// Auto-cleanup on page unload
window.addEventListener('beforeunload', () => {
    LMSManager.destroy();
});

console.log('QuantaFONS lms.js loaded successfully');
