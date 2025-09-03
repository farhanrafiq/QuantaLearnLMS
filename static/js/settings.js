// Settings management functionality
class SettingsManager {
    constructor() {
        this.currentSettings = {};
        this.init();
    }
    
    init() {
        this.loadSettings();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Handle form submissions for different setting categories
        const forms = [
            'generalSettingsForm',
            'preferencesForm', 
            'lmsSettingsForm',
            'transportSettingsForm',
            'notificationSettingsForm',
            'securitySettingsForm'
        ];
        
        forms.forEach(formId => {
            const form = document.getElementById(formId);
            if (form) {
                form.addEventListener('submit', (e) => this.handleFormSubmit(e, formId));
            }
        });
    }
    
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            
            this.currentSettings = {
                user: {},
                school: {}
            };
            
            // Process user settings
            data.user_settings.forEach(setting => {
                this.currentSettings.user[`${setting.category}.${setting.key}`] = setting;
            });
            
            // Process school settings
            data.school_settings.forEach(setting => {
                this.currentSettings.school[`${setting.category}.${setting.key}`] = setting;
            });
            
            this.populateFormFields();
            
        } catch (error) {
            console.error('Error loading settings:', error);
            this.showAlert('Failed to load settings', 'danger');
        }
    }
    
    populateFormFields() {
        // General settings (school-wide)
        this.setFieldValue('schoolTimezone', 'general.school_timezone', 'school');
        this.setFieldValue('dateFormat', 'general.date_format', 'school');
        this.setFieldValue('timeFormat', 'general.time_format', 'school');
        this.setFieldValue('defaultLanguage', 'general.default_language', 'school');
        
        // User preferences
        this.setFieldValue('theme', 'preferences.theme', 'user');
        this.setFieldValue('dashboardLayout', 'preferences.dashboard_layout', 'user');
        this.setFieldValue('itemsPerPage', 'preferences.items_per_page', 'user');
        this.setCheckboxValue('emailNotifications', 'preferences.email_notifications', 'user');
        
        // LMS settings (school-wide)
        this.setFieldValue('defaultAssignmentDuration', 'lms.default_assignment_duration_days', 'school');
        this.setFieldValue('maxFileUploadSize', 'lms.max_file_upload_size_mb', 'school');
        this.setCheckboxValue('allowLateSubmissions', 'lms.allow_late_submissions', 'school');
        this.setCheckboxValue('attendanceRequired', 'lms.attendance_required', 'school');
        
        // Transport settings (school-wide)
        this.setFieldValue('fuelAlertThreshold', 'transport.default_fuel_alert_threshold', 'school');
        this.setFieldValue('fuelEfficiencyTarget', 'transport.fuel_efficiency_target_kmpl', 'school');
        this.setFieldValue('maxSpeedLimit', 'transport.max_speed_limit_kmh', 'school');
        this.setFieldValue('telemetryRefreshInterval', 'transport.telemetry_refresh_interval_seconds', 'school');
        this.setCheckboxValue('geofenceAlertsEnabled', 'transport.geofence_alert_enabled', 'school');
        
        // Notification settings (school-wide)
        this.setCheckboxValue('emailNotificationsEnabled', 'notification.email_notifications_enabled', 'school');
        this.setCheckboxValue('smsNotificationsEnabled', 'notification.sms_notifications_enabled', 'school');
        this.setCheckboxValue('pushNotificationsEnabled', 'notification.push_notifications_enabled', 'school');
        this.setCheckboxValue('dailySummaryEnabled', 'notification.daily_summary_enabled', 'school');
        
        // Security settings (school-wide)
        this.setFieldValue('sessionTimeout', 'security.session_timeout_minutes', 'school');
        this.setFieldValue('passwordMinLength', 'security.password_min_length', 'school');
        this.setFieldValue('maxLoginAttempts', 'security.max_login_attempts', 'school');
        this.setFieldValue('lockoutDuration', 'security.lockout_duration_minutes', 'school');
        this.setCheckboxValue('requirePasswordComplexity', 'security.require_password_complexity', 'school');
    }
    
    setFieldValue(fieldId, settingKey, scope) {
        const field = document.getElementById(fieldId);
        const setting = this.currentSettings[scope][settingKey];
        
        if (field && setting) {
            field.value = setting.value;
        }
    }
    
    setCheckboxValue(fieldId, settingKey, scope) {
        const field = document.getElementById(fieldId);
        const setting = this.currentSettings[scope][settingKey];
        
        if (field && setting) {
            field.checked = setting.value === true || setting.value === 'true';
        }
    }
    
    async handleFormSubmit(event, formId) {
        event.preventDefault();
        
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        
        // Determine category and scope based on form
        let category, isSchoolSetting;
        
        switch (formId) {
            case 'generalSettingsForm':
                category = 'general';
                isSchoolSetting = true;
                break;
            case 'preferencesForm':
                category = 'preferences';
                isSchoolSetting = false;
                break;
            case 'lmsSettingsForm':
                category = 'lms';
                isSchoolSetting = true;
                break;
            case 'transportSettingsForm':
                category = 'transport';
                isSchoolSetting = true;
                break;
            case 'notificationSettingsForm':
                category = 'notification';
                isSchoolSetting = true;
                break;
            case 'securitySettingsForm':
                category = 'security';
                isSchoolSetting = true;
                break;
            default:
                category = 'general';
                isSchoolSetting = false;
        }
        
        // Save each form field as a separate setting
        const savePromises = [];
        
        for (let [key, value] of formData.entries()) {
            // Determine data type
            let dataType = 'string';
            const field = form.querySelector(`[name="${key}"]`);
            
            if (field) {
                if (field.type === 'checkbox') {
                    value = field.checked;
                    dataType = 'boolean';
                } else if (field.type === 'number') {
                    value = parseFloat(value);
                    dataType = field.step && field.step.includes('.') ? 'float' : 'integer';
                }
            }
            
            const settingData = {
                category: category,
                key: key,
                value: value,
                data_type: dataType,
                is_school_setting: isSchoolSetting
            };
            
            savePromises.push(this.saveSetting(settingData));
        }
        
        try {
            await Promise.all(savePromises);
            this.showAlert('Settings saved successfully!', 'success');
            
            // Reload settings to reflect changes
            await this.loadSettings();
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showAlert('Failed to save some settings', 'danger');
        }
    }
    
    async saveSetting(settingData) {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settingData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save setting');
        }
        
        return response.json();
    }
    
    showAlert(message, type = 'info') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.querySelector('.container-fluid');
        if (container) {
            const alertDiv = document.createElement('div');
            alertDiv.innerHTML = alertHtml;
            container.insertBefore(alertDiv.firstElementChild, container.firstChild);
            
            // Auto dismiss after 5 seconds
            setTimeout(() => {
                const alert = container.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }
    }
    
    // Utility method to get a specific setting value
    getSetting(category, key, scope = 'user', defaultValue = null) {
        const settingKey = `${category}.${key}`;
        const setting = this.currentSettings[scope][settingKey];
        return setting ? setting.value : defaultValue;
    }
    
    // Apply theme changes immediately
    applyThemeChanges(theme) {
        const body = document.body;
        body.classList.remove('theme-light', 'theme-dark');
        
        if (theme === 'dark') {
            body.classList.add('theme-dark');
        } else if (theme === 'light') {
            body.classList.add('theme-light');
        } else {
            // Auto theme - use system preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                body.classList.add('theme-dark');
            } else {
                body.classList.add('theme-light');
            }
        }
    }
    
    // Export settings as JSON
    exportSettings() {
        const settingsData = {
            user_settings: Object.values(this.currentSettings.user),
            school_settings: Object.values(this.currentSettings.school),
            exported_at: new Date().toISOString(),
            version: '1.0'
        };
        
        const dataStr = JSON.stringify(settingsData, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `school-settings-${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    }
}

// Initialize settings manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});

// Add export functionality
function exportSettings() {
    if (window.settingsManager) {
        window.settingsManager.exportSettings();
    }
}

console.log('Settings.js loaded successfully');