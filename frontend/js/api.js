/* ==========================================================================
   API Client
   ========================================================================== */

const API = {
    baseUrl: '/api',

    /**
     * Get the JWT token from localStorage.
     */
    getToken() {
        return localStorage.getItem('support_token');
    },

    /**
     * Set the JWT token in localStorage.
     */
    setToken(token) {
        localStorage.setItem('support_token', token);
    },

    /**
     * Clear the JWT token.
     */
    clearToken() {
        localStorage.removeItem('support_token');
        localStorage.removeItem('support_user');
    },

    /**
     * Get the stored user profile.
     */
    getUser() {
        const user = localStorage.getItem('support_user');
        return user ? JSON.parse(user) : null;
    },

    /**
     * Store user profile.
     */
    setUser(user) {
        localStorage.setItem('support_user', JSON.stringify(user));
    },

    /**
     * Check if user is authenticated.
     */
    isAuthenticated() {
        return !!this.getToken();
    },

    /**
     * Make an authenticated API request.
     */
    async request(method, path, body = null) {
        const headers = {
            'Content-Type': 'application/json',
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const options = { method, headers };
        if (body && method !== 'GET') {
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(`${this.baseUrl}${path}`, options);
            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    this.clearToken();
                    if (window.location.pathname.startsWith('/support') &&
                        !window.location.pathname.includes('/login')) {
                        Router.navigate('/support/login');
                    }
                }
                throw { status: response.status, ...data };
            }

            return data;
        } catch (error) {
            if (error.status) throw error;
            throw { status: 0, error: 'Network error. Please check your connection.' };
        }
    },

    // ==================== Customer API ====================

    /**
     * Submit a new complaint.
     */
    async submitComplaint(data) {
        return this.request('POST', '/customer/complaints', data);
    },

    /**
     * Track a complaint by reference number.
     */
    async trackComplaint(reference) {
        return this.request('GET', `/customer/complaints/${encodeURIComponent(reference)}`);
    },

    // ==================== Support API ====================

    /**
     * Login as support staff.
     */
    async login(username, password) {
        const result = await this.request('POST', '/support/login', { username, password });
        if (result.token) {
            this.setToken(result.token);
            this.setUser(result.user);
        }
        return result;
    },

    /**
     * Get current user profile.
     */
    async getMe() {
        return this.request('GET', '/support/me');
    },

    /**
     * Logout.
     */
    logout() {
        this.clearToken();
    },

    /**
     * List complaints (support).
     */
    async listComplaints(filters = {}) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, val]) => {
            if (val != null && val !== '') params.set(key, val);
        });
        const qs = params.toString();
        return this.request('GET', `/support/complaints${qs ? '?' + qs : ''}`);
    },

    /**
     * Get complaint details (support).
     */
    async getComplaint(id) {
        return this.request('GET', `/support/complaints/${id}`);
    },

    /**
     * Update a complaint.
     */
    async updateComplaint(id, data) {
        return this.request('PATCH', `/support/complaints/${id}`, data);
    },

    /**
     * Add a note to a complaint.
     */
    async addNote(complaintId, content) {
        return this.request('POST', `/support/complaints/${complaintId}/notes`, { content });
    },

    /**
     * Assign a complaint.
     */
    async assignComplaint(complaintId, data) {
        return this.request('POST', `/support/complaints/${complaintId}/assign`, data);
    },

    /**
     * Resolve a complaint.
     */
    async resolveComplaint(complaintId, resolutionNote = '') {
        return this.request('POST', `/support/complaints/${complaintId}/resolve`, {
            resolution_note: resolutionNote,
        });
    },

    /**
     * Reopen a complaint.
     */
    async reopenComplaint(complaintId, reason = '') {
        return this.request('POST', `/support/complaints/${complaintId}/reopen`, { reason });
    },

    /**
     * Get list of agents.
     */
    async listAgents() {
        return this.request('GET', '/support/agents');
    },

    /**
     * Get analytics overview.
     */
    async getAnalytics() {
        return this.request('GET', '/support/analytics/overview');
    },
};
