/* ==========================================================================
   Utility functions
   ========================================================================== */

const Utils = {
    /**
     * Format a date string into a human-readable format.
     */
    formatDate(dateStr) {
        if (!dateStr) return '—';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    },

    /**
     * Format a date with time.
     */
    formatDateTime(dateStr) {
        if (!dateStr) return '—';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    },

    /**
     * Format relative time (e.g., "2 hours ago").
     */
    formatRelativeTime(dateStr) {
        if (!dateStr) return '—';
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return Utils.formatDate(dateStr);
    },

    /**
     * Format confidence as percentage string.
     */
    formatConfidence(confidence) {
        if (confidence == null) return '—';
        return `${Math.round(confidence * 100)}%`;
    },

    /**
     * Get confidence level class.
     */
    getConfidenceLevel(confidence) {
        if (confidence >= 0.8) return 'high';
        if (confidence >= 0.6) return 'medium';
        return 'low';
    },

    /**
     * Format priority badge HTML.
     */
    priorityBadge(priority) {
        if (!priority) return '<span class="badge badge-medium">UNKNOWN</span>';
        return `<span class="badge badge-${priority}">${priority.toUpperCase()}</span>`;
    },

    /**
     * Format status badge HTML.
     */
    statusBadge(status) {
        const labels = {
            'submitted': 'Submitted',
            'under_review': 'Under Review',
            'in_progress': 'In Progress',
            'waiting_for_customer': 'Waiting for Customer',
            'resolved': 'Resolved',
            'closed': 'Closed',
        };
        const label = labels[status] || status;
        return `<span class="badge badge-status status-${status}">${label}</span>`;
    },

    /**
     * Format status label.
     */
    statusLabel(status) {
        const labels = {
            'submitted': 'Submitted',
            'under_review': 'Under Review',
            'in_progress': 'In Progress',
            'waiting_for_customer': 'Waiting for Customer',
            'resolved': 'Resolved',
            'closed': 'Closed',
        };
        return labels[status] || status;
    },

    /**
     * Truncate text to a maximum length.
     */
    truncate(text, maxLen = 100) {
        if (!text) return '';
        if (text.length <= maxLen) return text;
        return text.substring(0, maxLen) + '…';
    },

    /**
     * Escape HTML to prevent XSS.
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    /**
     * Show a toast notification.
     */
    showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('toast-out');
            setTimeout(() => toast.remove(), 200);
        }, duration);
    },

    /**
     * Debounce a function.
     */
    debounce(fn, delay = 300) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    /**
     * Get short category name.
     */
    shortCategory(category) {
        const map = {
            'Credit reporting, credit repair services, or other personal consumer reports': 'Credit Reporting',
            'Debt collection': 'Debt Collection',
            'Mortgage': 'Mortgage',
            'Credit card or prepaid card': 'Credit Card',
            'Checking or savings account': 'Bank Account',
            'Student loan': 'Student Loan',
            'Vehicle loan or lease': 'Vehicle Loan',
            'Money transfer, virtual currency, or money service': 'Money Transfer',
            'Payday loan, title loan, or personal loan': 'Personal Loan',
        };
        return map[category] || category || 'Unknown';
    },
};
