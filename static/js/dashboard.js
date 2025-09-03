// QuantaFONS Dashboard Management Module

const DashboardManager = {
    userRole: null,
    charts: {},
    refreshInterval: null,

    init(role) {
        this.userRole = role;
        this.setupEventListeners();
        this.loadStats();
        this.setupAutoRefresh();
        console.log(`Dashboard initialized for role: ${role}`);
    },

    setupEventListeners() {
        // Add event listeners for dashboard interactions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="refresh-stats"]')) {
                this.loadStats();
            }
        });
    },

    setupAutoRefresh() {
        // Refresh dashboard data every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.loadStats();
        }, 300000);
    },

    async loadStats() {
        try {
            const statsCards = document.getElementById('statsCards');
            if (!statsCards) return;

            // Show loading state
            window.QuantaFONS.LoadingManager.show('statsCards', 'Loading dashboard statistics...');

            // Load role-specific statistics
            const stats = await this.getRoleSpecificStats();
            this.renderStats(stats);

            // Load additional content based on role
            await this.loadRoleSpecificContent();

        } catch (error) {
            console.error('Error loading dashboard stats:', error);
            window.QuantaFONS.Utils.showToast('Failed to load dashboard data', 'error');
        }
    },

    async getRoleSpecificStats() {
        const stats = {};

        try {
            switch (this.userRole) {
                case 'SuperAdmin':
                case 'SchoolAdmin':
                    stats.courses = await window.QuantaFONS.API.get('/lms/courses');
                    stats.buses = await window.QuantaFONS.API.get('/transport/buses');
                    stats.alerts = await window.QuantaFONS.API.get('/transport/alerts');
                    break;

                case 'Teacher':
                    stats.courses = await window.QuantaFONS.API.get('/lms/courses');
                    break;

                case 'Student':
                    stats.courses = await window.QuantaFONS.API.get('/lms/courses');
                    break;

                case 'TransportManager':
                case 'Driver':
                    stats.buses = await window.QuantaFONS.API.get('/transport/buses');
                    stats.alerts = await window.QuantaFONS.API.get('/transport/alerts');
                    break;
            }
        } catch (error) {
            console.error('Error fetching role-specific stats:', error);
        }

        return stats;
    },

    renderStats(stats) {
        const statsCards = document.getElementById('statsCards');
        if (!statsCards) return;

        let cardsHTML = '';

        switch (this.userRole) {
            case 'SuperAdmin':
            case 'SchoolAdmin':
                cardsHTML = this.renderAdminStats(stats);
                break;
            case 'Teacher':
                cardsHTML = this.renderTeacherStats(stats);
                break;
            case 'Student':
                cardsHTML = this.renderStudentStats(stats);
                break;
            case 'TransportManager':
            case 'Driver':
                cardsHTML = this.renderTransportStats(stats);
                break;
            default:
                cardsHTML = this.renderDefaultStats();
        }

        statsCards.innerHTML = cardsHTML;
    },

    renderAdminStats(stats) {
        const totalCourses = stats.courses ? stats.courses.length : 0;
        const totalBuses = stats.buses ? stats.buses.length : 0;
        const activeBuses = stats.buses ? stats.buses.filter(bus => bus.is_active).length : 0;
        const activeAlerts = stats.alerts ? stats.alerts.filter(alert => !alert.is_acknowledged).length : 0;

        return `
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-primary mx-auto mb-3">
                            <i class="fas fa-graduation-cap"></i>
                        </div>
                        <h3 class="mb-1">${totalCourses}</h3>
                        <p class="text-muted mb-0">Total Courses</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-success mx-auto mb-3">
                            <i class="fas fa-bus"></i>
                        </div>
                        <h3 class="mb-1">${activeBuses}/${totalBuses}</h3>
                        <p class="text-muted mb-0">Active Buses</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-warning mx-auto mb-3">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                        <h3 class="mb-1">${activeAlerts}</h3>
                        <p class="text-muted mb-0">Active Alerts</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-info mx-auto mb-3">
                            <i class="fas fa-users"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Total Users</p>
                    </div>
                </div>
            </div>
        `;
    },

    renderTeacherStats(stats) {
        const totalCourses = stats.courses ? stats.courses.length : 0;
        const totalStudents = stats.courses ? 
            stats.courses.reduce((sum, course) => sum + (course.enrolled_students || 0), 0) : 0;

        return `
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-primary mx-auto mb-3">
                            <i class="fas fa-chalkboard-teacher"></i>
                        </div>
                        <h3 class="mb-1">${totalCourses}</h3>
                        <p class="text-muted mb-0">My Courses</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-success mx-auto mb-3">
                            <i class="fas fa-users"></i>
                        </div>
                        <h3 class="mb-1">${totalStudents}</h3>
                        <p class="text-muted mb-0">Total Students</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-warning mx-auto mb-3">
                            <i class="fas fa-clipboard-check"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Pending Reviews</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-info mx-auto mb-3">
                            <i class="fas fa-tasks"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Assignments</p>
                    </div>
                </div>
            </div>
        `;
    },

    renderStudentStats(stats) {
        const enrolledCourses = stats.courses ? stats.courses.length : 0;

        return `
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-primary mx-auto mb-3">
                            <i class="fas fa-book-open"></i>
                        </div>
                        <h3 class="mb-1">${enrolledCourses}</h3>
                        <p class="text-muted mb-0">Enrolled Courses</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-warning mx-auto mb-3">
                            <i class="fas fa-clock"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Pending Assignments</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-success mx-auto mb-3">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Completed</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-info mx-auto mb-3">
                            <i class="fas fa-percentage"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Average Grade</p>
                    </div>
                </div>
            </div>
        `;
    },

    renderTransportStats(stats) {
        const totalBuses = stats.buses ? stats.buses.length : 0;
        const activeBuses = stats.buses ? stats.buses.filter(bus => bus.is_active).length : 0;
        const activeAlerts = stats.alerts ? stats.alerts.filter(alert => !alert.is_acknowledged).length : 0;
        const onlineBuses = stats.buses ? 
            stats.buses.filter(bus => bus.latest_location && bus.latest_location.engine_on).length : 0;

        return `
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-primary mx-auto mb-3">
                            <i class="fas fa-bus"></i>
                        </div>
                        <h3 class="mb-1">${totalBuses}</h3>
                        <p class="text-muted mb-0">Total Buses</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-success mx-auto mb-3">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <h3 class="mb-1">${onlineBuses}</h3>
                        <p class="text-muted mb-0">Online Now</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-warning mx-auto mb-3">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                        <h3 class="mb-1">${activeAlerts}</h3>
                        <p class="text-muted mb-0">Active Alerts</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-3">
                <div class="card quantafons-card dashboard-card h-100">
                    <div class="card-body text-center">
                        <div class="stat-icon bg-info mx-auto mb-3">
                            <i class="fas fa-gas-pump"></i>
                        </div>
                        <h3 class="mb-1">--</h3>
                        <p class="text-muted mb-0">Avg Fuel Efficiency</p>
                    </div>
                </div>
            </div>
        `;
    },

    renderDefaultStats() {
        return `
            <div class="col-12">
                <div class="card quantafons-card">
                    <div class="card-body text-center py-5">
                        <i class="fas fa-tachometer-alt fa-3x text-muted mb-3"></i>
                        <h5>Welcome to QuantaFONS</h5>
                        <p class="text-muted">Your dashboard is being prepared...</p>
                    </div>
                </div>
            </div>
        `;
    },

    async loadRoleSpecificContent() {
        switch (this.userRole) {
            case 'Teacher':
                await this.loadTeacherContent();
                break;
            case 'Student':
                await this.loadStudentContent();
                break;
            case 'TransportManager':
            case 'Driver':
                await this.loadTransportContent();
                break;
        }
    },

    async loadTeacherContent() {
        try {
            const coursesElement = document.getElementById('teacherCourses');
            if (coursesElement) {
                const courses = await window.QuantaFONS.API.get('/lms/courses');
                this.renderTeacherCourses(courses, coursesElement);
            }

            const activityElement = document.getElementById('recentActivity');
            if (activityElement) {
                this.renderRecentActivity(activityElement);
            }
        } catch (error) {
            console.error('Error loading teacher content:', error);
        }
    },

    async loadStudentContent() {
        try {
            const coursesElement = document.getElementById('studentCourses');
            if (coursesElement) {
                const courses = await window.QuantaFONS.API.get('/lms/courses');
                this.renderStudentCourses(courses, coursesElement);
            }

            const assignmentsElement = document.getElementById('upcomingAssignments');
            if (assignmentsElement) {
                this.renderUpcomingAssignments(assignmentsElement);
            }
        } catch (error) {
            console.error('Error loading student content:', error);
        }
    },

    async loadTransportContent() {
        try {
            const fleetElement = document.getElementById('fleetStatus');
            if (fleetElement) {
                const buses = await window.QuantaFONS.API.get('/transport/buses');
                this.renderFleetStatus(buses, fleetElement);
            }

            const alertsElement = document.getElementById('activeAlerts');
            if (alertsElement) {
                const alerts = await window.QuantaFONS.API.get('/transport/alerts');
                this.renderActiveAlerts(alerts, alertsElement);
            }
        } catch (error) {
            console.error('Error loading transport content:', error);
        }
    },

    renderTeacherCourses(courses, element) {
        if (!courses || courses.length === 0) {
            window.QuantaFONS.LoadingManager.empty(element, 'No courses assigned yet');
            return;
        }

        const coursesHTML = courses.map(course => `
            <div class="course-card p-3 mb-2 rounded border">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${course.name}</h6>
                        <p class="mb-1 small text-muted">${course.description || 'No description'}</p>
                        <small class="text-muted">
                            <i class="fas fa-users me-1"></i>${course.enrolled_students || 0} students
                            <i class="fas fa-tasks ms-2 me-1"></i>${course.assignments_count || 0} assignments
                        </small>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/lms?course=${course.id}">
                                <i class="fas fa-eye me-1"></i>View Course
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="createAssignment(${course.id})">
                                <i class="fas fa-plus me-1"></i>New Assignment
                            </a></li>
                        </ul>
                    </div>
                </div>
            </div>
        `).join('');

        element.innerHTML = coursesHTML;
    },

    renderStudentCourses(courses, element) {
        if (!courses || courses.length === 0) {
            window.QuantaFONS.LoadingManager.empty(element, 'No courses enrolled yet');
            return;
        }

        const coursesHTML = courses.map(course => `
            <div class="course-card p-3 mb-2 rounded border">
                <h6 class="mb-1">${course.name}</h6>
                <p class="mb-1 small text-muted">${course.teacher_name || 'No teacher assigned'}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        <i class="fas fa-tasks me-1"></i>${course.assignments_count || 0} assignments
                    </small>
                    <a href="/lms?course=${course.id}" class="btn btn-sm quantafons-btn-primary">
                        View Course
                    </a>
                </div>
            </div>
        `).join('');

        element.innerHTML = coursesHTML;
    },

    renderFleetStatus(buses, element) {
        if (!buses || buses.length === 0) {
            window.QuantaFONS.LoadingManager.empty(element, 'No buses in fleet yet');
            return;
        }

        const fleetHTML = buses.slice(0, 5).map(bus => {
            const status = bus.latest_location && bus.latest_location.engine_on ? 'online' : 'offline';
            const statusClass = status === 'online' ? 'text-success' : 'text-danger';
            const fuelLevel = bus.latest_location ? bus.latest_location.fuel_level || 0 : 0;
            const fuelPercentage = bus.fuel_tank_capacity > 0 ? 
                Math.round((fuelLevel / bus.fuel_tank_capacity) * 100) : 0;

            return `
                <div class="bus-card p-3 mb-2 rounded border" onclick="showBusDetails(${bus.id})">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${bus.name}</h6>
                            <small class="text-muted">${bus.registration_no}</small>
                        </div>
                        <div class="text-end">
                            <span class="badge bg-${status === 'online' ? 'success' : 'secondary'} mb-1">
                                ${status.toUpperCase()}
                            </span>
                            <div class="small">
                                <div class="fuel-gauge mb-1" style="width: 60px;">
                                    <div class="fuel-level fuel-${fuelPercentage > 50 ? 'high' : fuelPercentage > 20 ? 'medium' : 'low'}" 
                                         style="width: ${fuelPercentage}%"></div>
                                </div>
                                <span class="text-muted">${fuelPercentage}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        element.innerHTML = fleetHTML;
    },

    renderActiveAlerts(alerts, element) {
        const activeAlerts = alerts ? alerts.filter(alert => !alert.is_acknowledged) : [];

        if (activeAlerts.length === 0) {
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                    <p>No active alerts</p>
                </div>
            `;
            return;
        }

        const alertsHTML = activeAlerts.slice(0, 5).map(alert => `
            <div class="alert-item alert-${alert.level.toLowerCase()} p-2 mb-2 rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1 small">${alert.title}</h6>
                        <p class="mb-1 text-muted" style="font-size: 0.75rem;">${alert.message}</p>
                        <small class="text-muted">${window.QuantaFONS.Utils.timeAgo(alert.timestamp)}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="acknowledgeAlert(${alert.id})">
                        <i class="fas fa-check"></i>
                    </button>
                </div>
            </div>
        `).join('');

        element.innerHTML = alertsHTML;
    },

    renderRecentActivity(element) {
        element.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-clock fa-2x mb-2"></i>
                <p>Activity tracking coming soon</p>
            </div>
        `;
    },

    renderUpcomingAssignments(element) {
        element.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-tasks fa-2x mb-2"></i>
                <p>No upcoming assignments</p>
            </div>
        `;
    },

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Destroy any charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
};

// Make DashboardManager globally available
window.DashboardManager = DashboardManager;

// Auto-cleanup on page unload
window.addEventListener('beforeunload', () => {
    DashboardManager.destroy();
});

console.log('QuantaFONS dashboard.js loaded successfully');
