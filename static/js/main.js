// QuantaFONS Main JavaScript Module
// Global utilities and shared functionality

// Global app state
window.QuantaFONS = {
    user: null,
    socket: null,
    config: {
        apiBaseUrl: '/api',
        socketNamespace: '/'
    }
};

// Initialize Socket.IO connection
function initializeSocket() {
    if (typeof io !== 'undefined') {
        window.QuantaFONS.socket = io(window.QuantaFONS.config.socketNamespace);
        
        window.QuantaFONS.socket.on('connect', function() {
            console.log('Connected to QuantaFONS server');
        });
        
        window.QuantaFONS.socket.on('disconnect', function() {
            console.log('Disconnected from QuantaFONS server');
        });
        
        // Join appropriate rooms based on user role
        if (window.location.pathname.includes('/transport')) {
            window.QuantaFONS.socket.emit('join_transport_room');
        }
        
        return window.QuantaFONS.socket;
    }
    return null;
}

// API Helper Functions
const API = {
    async request(endpoint, options = {}) {
        const url = `${window.QuantaFONS.config.apiBaseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
};

// Utility Functions
const Utils = {
    // Format date for display
    formatDate(date, options = {}) {
        if (!date) return 'N/A';
        const d = typeof date === 'string' ? new Date(date) : date;
        const defaultOptions = { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        };
        return d.toLocaleDateString('en-US', { ...defaultOptions, ...options });
    },
    
    // Format datetime for display
    formatDateTime(date, options = {}) {
        if (!date) return 'N/A';
        const d = typeof date === 'string' ? new Date(date) : date;
        const defaultOptions = { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        return d.toLocaleDateString('en-US', { ...defaultOptions, ...options });
    },
    
    // Calculate time ago
    timeAgo(date) {
        if (!date) return 'Never';
        const now = new Date();
        const then = typeof date === 'string' ? new Date(date) : date;
        const diffMs = now - then;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return this.formatDate(then);
    },
    
    // Show toast notification
    showToast(message, type = 'info') {
        const toastContainer = this.getToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },
    
    // Get or create toast container
    getToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1055';
            document.body.appendChild(container);
        }
        return container;
    },
    
    // Debounce function
    debounce(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    },
    
    // Validate email
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },
    
    // Generate random color
    generateColor(seed) {
        const colors = [
            '#2563eb', '#7c3aed', '#10b981', '#f59e0b', '#ef4444',
            '#06b6d4', '#8b5cf6', '#84cc16', '#f97316', '#ec4899'
        ];
        return colors[seed % colors.length];
    },
    
    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Copy to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy text: ', err);
            this.showToast('Failed to copy to clipboard', 'error');
        }
    },
    
    // Format currency
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },
    
    // Calculate percentage
    calculatePercentage(value, total) {
        if (total === 0) return 0;
        return Math.round((value / total) * 100);
    }
};

// Loading State Manager
const LoadingManager = {
    show(element, message = 'Loading...') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <div class="loading-spinner mb-2"></div>
                    <p>${message}</p>
                </div>
            `;
        }
    },
    
    hide(element, content = '') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.innerHTML = content;
        }
    },
    
    error(element, message = 'An error occurred') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2 text-warning"></i>
                    <p>${message}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
                        <i class="fas fa-sync-alt me-1"></i>Retry
                    </button>
                </div>
            `;
        }
    },
    
    empty(element, message = 'No data available') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        if (element) {
            element.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>${message}</p>
                </div>
            `;
        }
    }
};

// Form Validation Helper
const FormValidator = {
    validateForm(formElement) {
        const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            this.clearError(input);
            
            if (!input.value.trim()) {
                this.showError(input, 'This field is required');
                isValid = false;
            } else if (input.type === 'email' && !Utils.isValidEmail(input.value)) {
                this.showError(input, 'Please enter a valid email address');
                isValid = false;
            } else if (input.type === 'password' && input.value.length < 6) {
                this.showError(input, 'Password must be at least 6 characters');
                isValid = false;
            }
        });
        
        return isValid;
    },
    
    showError(input, message) {
        input.classList.add('is-invalid');
        
        let feedback = input.parentNode.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentNode.appendChild(feedback);
        }
        feedback.textContent = message;
    },
    
    clearError(input) {
        input.classList.remove('is-invalid');
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    },
    
    clearAllErrors(formElement) {
        const inputs = formElement.querySelectorAll('.is-invalid');
        inputs.forEach(input => this.clearError(input));
    }
};

// Storage Helper
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(`quantafons_${key}`, JSON.stringify(value));
        } catch (e) {
            console.error('Failed to save to localStorage:', e);
        }
    },
    
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(`quantafons_${key}`);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Failed to read from localStorage:', e);
            return defaultValue;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(`quantafons_${key}`);
        } catch (e) {
            console.error('Failed to remove from localStorage:', e);
        }
    },
    
    clear() {
        try {
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith('quantafons_')) {
                    localStorage.removeItem(key);
                }
            });
        } catch (e) {
            console.error('Failed to clear localStorage:', e);
        }
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO if available
    if (document.body.classList.contains('quantafons-body')) {
        initializeSocket();
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Export global utilities
window.QuantaFONS.API = API;
window.QuantaFONS.Utils = Utils;
window.QuantaFONS.LoadingManager = LoadingManager;
window.QuantaFONS.FormValidator = FormValidator;
window.QuantaFONS.Storage = Storage;

// Log initialization
console.log('QuantaFONS main.js loaded successfully');
