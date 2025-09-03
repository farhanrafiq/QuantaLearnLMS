// Form handling for School Management System
class FormHandler {
    static init() {
        this.setupFormHandlers();
        this.setupValidation();
        this.loadCourseOptions();
    }
    
    static setupFormHandlers() {
        // Handle create course form
        this.handleForm('createCourseForm', '/api/lms/courses', 'createCourseModal', 'Course created successfully!');
        
        // Handle create assignment form  
        this.handleForm('createAssignmentForm', '/api/lms/assignments', 'createAssignmentModal', 'Assignment created successfully!');
        
        // Handle create user form
        this.handleForm('createUserForm', '/api/users', 'createUserModal', 'User created successfully!');
        
        // Handle create bus form
        this.handleForm('createBusForm', '/api/transport/buses', 'createBusModal', 'Bus created successfully!');
    }
    
    static handleForm(formId, apiEndpoint, modalId, successMessage) {
        const form = document.getElementById(formId);
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            // Convert numeric fields
            if (data.capacity) data.capacity = parseInt(data.capacity);
            if (data.credits) data.credits = parseInt(data.credits);
            if (data.max_grade) data.max_grade = parseFloat(data.max_grade);
            if (data.fuel_tank_capacity) data.fuel_tank_capacity = parseFloat(data.fuel_tank_capacity);
            
            try {
                const response = await fetch(apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    this.closeModal(modalId);
                    form.reset();
                    this.showAlert(successMessage, 'success');
                    this.refreshPage();
                } else {
                    this.showAlert(result.error || 'Operation failed', 'danger');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                this.showAlert('Network error occurred', 'danger');
            }
        });
    }
    
    static closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        }
    }
    
    static showAlert(message, type = 'info') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.querySelector('.main-content');
        if (container) {
            const alertDiv = document.createElement('div');
            alertDiv.innerHTML = alertHtml;
            container.insertBefore(alertDiv.firstElementChild, container.firstChild);
            
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }
    }
    
    static refreshPage() {
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    }
    
    static setupValidation() {
        // Email validation
        const emailInputs = document.querySelectorAll('input[type="email"]');
        emailInputs.forEach(input => {
            input.addEventListener('blur', (e) => {
                const email = e.target.value;
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                
                if (email && !emailRegex.test(email)) {
                    e.target.classList.add('is-invalid');
                    this.showFieldError(e.target, 'Please enter a valid email address');
                } else {
                    e.target.classList.remove('is-invalid');
                    this.clearFieldError(e.target);
                }
            });
        });
        
        // Password confirmation
        const confirmPasswordInputs = document.querySelectorAll('#userConfirmPassword');
        confirmPasswordInputs.forEach(input => {
            input.addEventListener('blur', (e) => {
                const password = document.getElementById('userPassword').value;
                const confirmPassword = e.target.value;
                
                if (confirmPassword && password !== confirmPassword) {
                    e.target.classList.add('is-invalid');
                    this.showFieldError(e.target, 'Passwords do not match');
                } else {
                    e.target.classList.remove('is-invalid');
                    this.clearFieldError(e.target);
                }
            });
        });
    }
    
    static showFieldError(input, message) {
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = message;
        } else {
            const div = document.createElement('div');
            div.className = 'invalid-feedback';
            div.textContent = message;
            input.parentNode.appendChild(div);
        }
    }
    
    static clearFieldError(input) {
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }
    
    static async loadCourseOptions() {
        const courseSelect = document.getElementById('assignmentCourse');
        if (!courseSelect) return;
        
        try {
            const response = await fetch('/api/lms/courses');
            const courses = await response.json();
            
            courseSelect.innerHTML = '<option value="">Select Course</option>';
            courses.forEach(course => {
                const option = document.createElement('option');
                option.value = course.id;
                option.textContent = `${course.name} (${course.teacher_name})`;
                courseSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load courses:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    FormHandler.init();
});

console.log('Forms.js loaded successfully');