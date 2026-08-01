const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://facial-attendance-api-yqgp.onrender.com';

const api = {
    async request(method, endpoint, data = null, isFormData = false) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000);

        const options = {
            method,
            headers: {},
            cache: 'no-store',
            signal: controller.signal,
        };

        if (data) {
            if (isFormData) {
                options.body = data;
            } else {
                options.headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(data);
            }
        }

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            const result = await response.json();

            if (!response.ok) {
                throw { status: response.status, data: result };
            }

            return result;
        } catch (err) {
            if (err.name === 'AbortError') {
                throw { status: 503, data: { detail: 'timeout' } };
            }
            throw err;
        } finally {
            clearTimeout(timeoutId);
        }
    },

    // Students
    listStudents() {
        return this.request('GET', '/students');
    },

    getStudent(id) {
        return this.request('GET', `/students/${id}`);
    },

    createStudent(data) {
        return this.request('POST', '/students', data);
    },

    deleteStudent(id) {
        return this.request('DELETE', `/students/${id}`);
    },

    updateStudent(id, data) {
        return this.request('PUT', `/students/${id}`, data);
    },

    registerFace(studentId, formData) {
        return this.request('POST', `/students/${studentId}/register-face`, formData, true);
    },

    // Recognition
    recognize(formData) {
        return this.request('POST', '/recognize', formData, true);
    },

    // Attendance
    listAttendances(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request('GET', `/attendances${query ? '?' + query : ''}`);
    },

    // Eklesia sync
    syncToEklesia(classId, gradeId) {
        return this.request('POST', `/eklesia/sync?class_id=${classId}&grade_id=${gradeId}`);
    },

    // Stats
    getStats() {
        return this.request('GET', '/stats');
    },

    // Notifications
    sendNotification(studentId, message) {
        return this.request('POST', '/notify', { student_id: studentId, message });
    },

    // Health
    async healthCheck() {
        try {
            const result = await this.request('GET', '/health');
            return { online: true, ...result };
        } catch {
            return { online: false };
        }
    },

    // WhatsApp
    async getWhatsAppStatus() {
        try {
            const result = await this.request('GET', '/whatsapp-status');
            return result;
        } catch {
            return { status: 'offline' };
        }
    },

    // Classes
    listClasses() {
        return this.request('GET', '/classes');
    },

    getClass(id) {
        return this.request('GET', `/classes/${id}`);
    },

    createClass(data) {
        return this.request('POST', '/classes', data);
    },

    deleteClass(id) {
        return this.request('DELETE', `/classes/${id}`);
    },

    addStudentToClass(classId, studentId) {
        return this.request('POST', `/classes/${classId}/students`, { student_id: studentId });
    },

    removeStudentFromClass(classId, studentId) {
        return this.request('DELETE', `/classes/${classId}/students/${studentId}`);
    },

    listClassStudents(classId) {
        return this.request('GET', `/classes/${classId}/students`);
    },

    // Auth
    checkEmail(email) {
        return this.request('GET', `/auth/check-email?email=${encodeURIComponent(email)}`);
    },

    registerAdmin(data) {
        return this.request('POST', '/auth/register', data, true);
    },

    loginAdmin(data) {
        return this.request('POST', '/auth/login', data);
    },

    loginFace(formData) {
        return this.request('POST', '/auth/login-face', formData, true);
    },

    registerAdminFace(adminId, formData) {
        return this.request('POST', `/auth/register-face?admin_id=${adminId}`, formData, true);
    },

    getMe(token) {
        return this.request('GET', `/auth/me?token=${token}`);
    }
};
