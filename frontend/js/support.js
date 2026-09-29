/* ==========================================================================
   Support Staff Portal
   ========================================================================== */

const SupportPortal = {
    /**
     * Render the support navigation bar.
     */
    renderNav() {
        const navbar = document.getElementById('navbar');
        const path = window.location.pathname;
        const user = API.getUser();

        if (!user) {
            navbar.innerHTML = `
                <a href="/support/login" class="navbar-brand">
                    <div class="brand-icon">⚙️</div>
                    <span>Support Portal</span>
                </a>
            `;
            document.body.classList.remove('theme-light');
            return;
        }

        const initials = user.display_name
            ? user.display_name.split(' ').map(w => w[0]).join('').toUpperCase().substring(0, 2)
            : 'U';

        navbar.innerHTML = `
            <a href="/support" class="navbar-brand" onclick="event.preventDefault(); Router.navigate('/support')">
                <div class="brand-icon">⚙️</div>
                <span>Support Portal</span>
            </a>
            <ul class="navbar-nav" id="support-nav-menu">
                <li><a href="/support" class="${path === '/support' ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/support')">📊 Dashboard</a></li>
                <li><a href="/support/complaints" class="${path.startsWith('/support/complaints') ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/support/complaints')">📋 Queue</a></li>
                <li><a href="/support/analytics" class="${path === '/support/analytics' ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/support/analytics')">📈 Analytics</a></li>
                ${user.role === 'admin' ? `
                <li><a href="/support/settings" class="${path === '/support/settings' ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/support/settings')">⚙️ Settings</a></li>
                ` : ''}
            </ul>
            <div class="navbar-actions">
                <div class="navbar-user">
                    <div class="user-avatar">${initials}</div>
                    <div>
                        <div class="user-name-text" style="font-size: 0.875rem; font-weight: 500; color: var(--color-text);">${Utils.escapeHtml(user.display_name)}</div>
                        <div class="user-role">${user.role}</div>
                    </div>
                </div>
                <button class="btn btn-sm btn-secondary" onclick="SupportPortal.logout()">Logout</button>
            </div>
            <button class="navbar-toggle" id="support-nav-toggle" aria-label="Toggle navigation">☰</button>
        `;

        document.getElementById('support-nav-toggle').addEventListener('click', () => {
            document.getElementById('support-nav-menu').classList.toggle('show');
        });

        // Dark theme for support portal
        document.body.classList.remove('theme-light');
    },

    /**
     * Check authentication and redirect if needed.
     */
    requireAuth() {
        if (!API.isAuthenticated()) {
            Router.navigate('/support/login');
            return false;
        }
        return true;
    },

    /**
     * Logout.
     */
    logout() {
        API.logout();
        Router.navigate('/support/login');
        Utils.showToast('Logged out successfully', 'info');
    },

    // ==================== Login ====================

    renderLogin() {
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="login-container page-enter">
                <div class="card login-card">
                    <h2>Support Login</h2>
                    <p class="login-subtitle">Sign in to access the support dashboard</p>

                    <form id="login-form">
                        <div class="form-group">
                            <label class="form-label" for="login-username">Username</label>
                            <input type="text" id="login-username" class="form-input"
                                   placeholder="Enter your username" required autocomplete="username">
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="login-password">Password</label>
                            <input type="password" id="login-password" class="form-input"
                                   placeholder="Enter your password" required autocomplete="current-password">
                        </div>

                        <div id="login-error" class="form-error" style="display:none; margin-bottom: 1rem;"></div>

                        <button type="submit" id="login-btn" class="btn btn-primary btn-lg btn-block">
                            Sign In
                        </button>
                    </form>

                    <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--color-border);">
                        <p style="font-size: 0.75rem; color: var(--color-secondary-text); text-align: center;">
                            Demo accounts: admin / manager / agent1 (password from .env)
                        </p>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('login-btn');
            const errorDiv = document.getElementById('login-error');

            const username = document.getElementById('login-username').value.trim();
            const password = document.getElementById('login-password').value;

            if (!username || !password) {
                errorDiv.textContent = 'Username and password are required';
                errorDiv.style.display = 'block';
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<div class="spinner spinner-inline"></div> Signing in...';
            errorDiv.style.display = 'none';

            try {
                await API.login(username, password);
                Utils.showToast('Welcome back!', 'success');
                Router.navigate('/support');
            } catch (error) {
                errorDiv.textContent = error.error || 'Login failed';
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Sign In';
            }
        });
    },

    // ==================== Dashboard ====================

    async renderDashboard() {
        if (!this.requireAuth()) return;
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container wide page-enter">
                <div class="action-bar">
                    <h1>Dashboard</h1>
                    <div class="actions">
                        <button class="btn btn-secondary btn-sm" onclick="SupportPortal.renderDashboard()">🔄 Refresh</button>
                    </div>
                </div>
                <div class="loading-screen" id="dashboard-loader">
                    <div class="spinner"></div>
                    <p>Loading dashboard...</p>
                </div>
                <div id="dashboard-content" style="display: none;"></div>
            </div>
        `;

        try {
            const data = await API.getAnalytics();
            document.getElementById('dashboard-loader').style.display = 'none';
            const content = document.getElementById('dashboard-content');
            content.style.display = 'block';

            const bp = data.by_priority || {};

            content.innerHTML = `
                <div class="stat-cards">
                    <div class="stat-card">
                        <div class="stat-icon" style="background: transparent;">📋</div>
                        <div class="stat-value">${data.total_open || 0}</div>
                        <div class="stat-label">Open Complaints</div>
                    </div>
                    <div class="stat-card critical">
                        <div class="stat-icon">⚠️</div>
                        <div class="stat-value">${bp.critical || 0}</div>
                        <div class="stat-label">Critical</div>
                    </div>
                    <div class="stat-card high">
                        <div class="stat-icon">🔺</div>
                        <div class="stat-value">${bp.high || 0}</div>
                        <div class="stat-label">High Priority</div>
                    </div>
                    <div class="stat-card medium">
                        <div class="stat-icon">➡️</div>
                        <div class="stat-value">${bp.medium || 0}</div>
                        <div class="stat-label">Medium</div>
                    </div>
                    <div class="stat-card low">
                        <div class="stat-icon">⬇️</div>
                        <div class="stat-value">${bp.low || 0}</div>
                        <div class="stat-label">Low</div>
                    </div>
                </div>

                <div class="stat-cards" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));">
                    <div class="stat-card">
                        <div class="stat-value" style="font-size: 1.5rem;">${data.needs_review || 0}</div>
                        <div class="stat-label">Needs Review</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="font-size: 1.5rem;">${data.unassigned || 0}</div>
                        <div class="stat-label">Unassigned</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="font-size: 1.5rem;">${data.total_resolved || 0}</div>
                        <div class="stat-label">Resolved</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="font-size: 1.5rem;">${data.total || 0}</div>
                        <div class="stat-label">Total All Time</div>
                    </div>
                </div>

                <div class="dashboard-grid">
                    <div>
                        <div class="card dashboard-section">
                            <div class="dashboard-section-title">📊 Complaints by Category</div>
                            <div class="bar-chart">
                                ${this._renderCategoryChart(data.by_category || [])}
                            </div>
                        </div>

                        <div class="card dashboard-section">
                            <div class="dashboard-section-title">🕐 Recent Complaints</div>
                            ${this._renderRecentTable(data.recent_complaints || [])}
                        </div>
                    </div>
                    <div>
                        <div class="card dashboard-section">
                            <div class="dashboard-section-title">📈 Status Distribution</div>
                            <div class="bar-chart">
                                ${this._renderStatusChart(data.by_status || [])}
                            </div>
                        </div>

                        <div class="card dashboard-section">
                            <div class="dashboard-section-title">✅ Recently Resolved</div>
                            ${this._renderRecentResolved(data.recently_resolved || [])}
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            document.getElementById('dashboard-loader').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <h3>Failed to Load Dashboard</h3>
                    <p>${Utils.escapeHtml(error.error || 'Unable to load analytics data.')}</p>
                </div>
            `;
        }
    },

    _renderCategoryChart(categories) {
        if (!categories.length) return '<p style="color: var(--color-secondary-text);">No data available</p>';
        const max = Math.max(...categories.map(c => c.count), 1);
        return categories.map(c => {
            const pct = (c.count / max) * 100;
            return `
                <div class="bar-chart-item">
                    <div class="bar-chart-label" title="${Utils.escapeHtml(c.category)}">${Utils.shortCategory(c.category)}</div>
                    <div class="bar-chart-track">
                        <div class="bar-chart-fill" style="width: ${pct}%"></div>
                    </div>
                    <div class="bar-chart-value">${c.count}</div>
                </div>
            `;
        }).join('');
    },

    _renderStatusChart(statuses) {
        if (!statuses.length) return '<p style="color: var(--color-secondary-text);">No data available</p>';
        const max = Math.max(...statuses.map(s => s.count), 1);
        return statuses.map(s => {
            const pct = (s.count / max) * 100;
            return `
                <div class="bar-chart-item">
                    <div class="bar-chart-label">${Utils.statusLabel(s.status)}</div>
                    <div class="bar-chart-track">
                        <div class="bar-chart-fill" style="width: ${pct}%"></div>
                    </div>
                    <div class="bar-chart-value">${s.count}</div>
                </div>
            `;
        }).join('');
    },

    _renderRecentTable(complaints) {
        if (!complaints.length) {
            return '<div class="empty-state"><p>No recent complaints</p></div>';
        }
        return `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Reference</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Created</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${complaints.slice(0, 5).map(c => `
                            <tr class="clickable-row" onclick="Router.navigate('/support/complaints/${c.id}')">
                                <td style="font-family: monospace; font-weight: 600;">${Utils.escapeHtml(c.reference)}</td>
                                <td>${Utils.priorityBadge(c.current_priority)}</td>
                                <td>${Utils.statusBadge(c.status)}</td>
                                <td style="color: var(--color-secondary-text); font-size: 0.75rem;">${Utils.formatRelativeTime(c.created_at)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    },

    _renderRecentResolved(complaints) {
        if (!complaints.length) {
            return '<div class="empty-state"><p>No recently resolved complaints</p></div>';
        }
        return complaints.slice(0, 5).map(c => `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); cursor: pointer;"
                 onclick="Router.navigate('/support/complaints/${c.id}')">
                <div>
                    <div style="font-family: monospace; font-weight: 600; font-size: 0.875rem;">${Utils.escapeHtml(c.reference)}</div>
                    <div style="font-size: 0.75rem; color: var(--color-secondary-text);">${Utils.shortCategory(c.current_category)}</div>
                </div>
                <div style="font-size: 0.75rem; color: var(--color-primary);">✓ Resolved</div>
            </div>
        `).join('');
    },

    // ==================== Complaint Queue ====================

    async renderQueue() {
        if (!this.requireAuth()) return;
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container wide page-enter">
                <div class="action-bar">
                    <h1>Complaint Queue</h1>
                    <div class="actions">
                        <button class="btn btn-secondary btn-sm" onclick="SupportPortal.renderQueue()">🔄 Refresh</button>
                    </div>
                </div>

                <div class="filters-bar" id="queue-filters">
                    <input type="text" class="form-input search-input" id="filter-search"
                           placeholder="🔍 Search complaints...">
                    <select class="form-select" id="filter-priority">
                        <option value="">All Priorities</option>
                        <option value="critical">⚠️ Critical</option>
                        <option value="high">🔺 High</option>
                        <option value="medium">➡️ Medium</option>
                        <option value="low">⬇️ Low</option>
                    </select>
                    <select class="form-select" id="filter-status">
                        <option value="">All Statuses</option>
                        <option value="submitted">Submitted</option>
                        <option value="under_review">Under Review</option>
                        <option value="in_progress">In Progress</option>
                        <option value="waiting_for_customer">Waiting for Customer</option>
                        <option value="resolved">Resolved</option>
                        <option value="closed">Closed</option>
                    </select>
                    <select class="form-select" id="filter-review">
                        <option value="">All Reviews</option>
                        <option value="true">Needs Human Review</option>
                        <option value="false">Auto-Classified</option>
                    </select>
                </div>

                <div id="queue-content">
                    <div class="loading-screen">
                        <div class="spinner"></div>
                        <p>Loading complaints...</p>
                    </div>
                </div>
            </div>
        `;

        // Set up filter listeners
        const filterHandler = Utils.debounce(() => this._loadQueue(), 300);
        ['filter-search', 'filter-priority', 'filter-status', 'filter-review'].forEach(id => {
            document.getElementById(id).addEventListener('input', filterHandler);
            document.getElementById(id).addEventListener('change', filterHandler);
        });

        await this._loadQueue();
    },

    async _loadQueue() {
        const content = document.getElementById('queue-content');

        const filters = {
            search: document.getElementById('filter-search')?.value || '',
            priority: document.getElementById('filter-priority')?.value || '',
            status: document.getElementById('filter-status')?.value || '',
            needs_human_review: document.getElementById('filter-review')?.value || '',
        };

        // Remove empty
        Object.keys(filters).forEach(k => { if (!filters[k]) delete filters[k]; });

        try {
            const data = await API.listComplaints(filters);
            const complaints = data.complaints || [];

            if (!complaints.length) {
                content.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">📭</div>
                        <h3>No Complaints Found</h3>
                        <p>Try adjusting your filters or check back later.</p>
                    </div>
                `;
                return;
            }

            content.innerHTML = `
                <div style="margin-bottom: 0.75rem; font-size: 0.875rem; color: var(--color-secondary-text);">
                    Showing ${complaints.length} complaint${complaints.length === 1 ? '' : 's'}
                </div>
                <div class="table-container">
                    <table class="data-table" id="complaints-table">
                        <thead>
                            <tr>
                                <th>Reference</th>
                                <th>Complaint</th>
                                <th>Category</th>
                                <th>Priority</th>
                                <th>Confidence</th>
                                <th>Status</th>
                                <th>Assigned</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${complaints.map(c => `
                                <tr class="clickable-row" onclick="Router.navigate('/support/complaints/${c.id}')">
                                    <td style="font-family: monospace; font-weight: 600; white-space: nowrap;">${Utils.escapeHtml(c.reference)}</td>
                                    <td><div class="truncate" title="${Utils.escapeHtml(c.description)}">${Utils.escapeHtml(Utils.truncate(c.description, 60))}</div></td>
                                    <td style="white-space: nowrap;">${Utils.escapeHtml(Utils.shortCategory(c.current_category))}</td>
                                    <td>${Utils.priorityBadge(c.current_priority)}</td>
                                    <td>
                                        ${Utils.formatConfidence(c.system_confidence)}
                                        ${c.needs_human_review ? ' <span class="badge badge-review">Review</span>' : ''}
                                    </td>
                                    <td>${Utils.statusBadge(c.status)}</td>
                                    <td style="font-size: 0.75rem; color: var(--color-secondary-text);">
                                        ${Utils.escapeHtml(c.assignee_name || c.assigned_team || '—')}
                                    </td>
                                    <td style="font-size: 0.75rem; color: var(--color-secondary-text); white-space: nowrap;">
                                        ${Utils.formatRelativeTime(c.created_at)}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (error) {
            content.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <h3>Failed to Load Queue</h3>
                    <p>${Utils.escapeHtml(error.error || 'Unable to load complaints.')}</p>
                </div>
            `;
        }
    },

    // ==================== Complaint Detail ====================

    async renderComplaintDetail(id) {
        if (!this.requireAuth()) return;
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container wide">
                <div class="loading-screen">
                    <div class="spinner"></div>
                    <p>Loading complaint details...</p>
                </div>
            </div>
        `;

        try {
            const complaint = await API.getComplaint(id);
            const user = API.getUser();
            this._renderComplaintDetailContent(complaint, user, main);
        } catch (error) {
            main.innerHTML = `
                <div class="page-container narrow page-enter">
                    <div class="empty-state">
                        <div class="empty-icon">❌</div>
                        <h3>Complaint Not Found</h3>
                        <p>${Utils.escapeHtml(error.error || 'Unable to load this complaint.')}</p>
                        <br>
                        <a href="/support/complaints" class="btn btn-primary"
                           onclick="event.preventDefault(); Router.navigate('/support/complaints')">Back to Queue</a>
                    </div>
                </div>
            `;
        }
    },

    _renderComplaintDetailContent(c, user, main) {
        const canEditPriority = user && (user.role === 'admin' || user.role === 'manager');
        const canAssign = user && (user.role === 'admin' || user.role === 'manager');
        const confidenceLevel = Utils.getConfidenceLevel(c.system_confidence);
        const confidencePct = c.system_confidence ? Math.round(c.system_confidence * 100) : 0;

        // Check for overrides
        const categoryOverridden = c.manual_category && c.manual_category !== c.system_category;
        const priorityOverridden = c.manual_priority && c.manual_priority !== c.system_priority;

        main.innerHTML = `
            <div class="page-container wide page-enter">
                <div class="page-header">
                    <div class="breadcrumbs">
                        <a href="/support" onclick="event.preventDefault(); Router.navigate('/support')">Dashboard</a>
                        <span class="separator">›</span>
                        <a href="/support/complaints" onclick="event.preventDefault(); Router.navigate('/support/complaints')">Queue</a>
                        <span class="separator">›</span>
                        <span>${Utils.escapeHtml(c.reference)}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
                        <h1>${Utils.escapeHtml(c.reference)}</h1>
                        ${Utils.priorityBadge(c.current_priority)}
                        ${Utils.statusBadge(c.status)}
                        ${c.needs_human_review ? '<span class="badge badge-review">⚠ Needs Human Review</span>' : ''}
                    </div>
                </div>

                <div class="detail-grid">
                    <!-- Left column: Main content -->
                    <div>
                        <!-- Customer Information -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Customer Information</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                <div class="detail-field">
                                    <div class="detail-field-label">Name</div>
                                    <div class="detail-field-value">${Utils.escapeHtml(c.customer_name)}</div>
                                </div>
                                <div class="detail-field">
                                    <div class="detail-field-label">Email</div>
                                    <div class="detail-field-value">${Utils.escapeHtml(c.customer_email)}</div>
                                </div>
                            </div>
                        </div>

                        <!-- Complaint Text -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Original Complaint</div>
                            <div class="complaint-text">${Utils.escapeHtml(c.description)}</div>
                        </div>

                        <!-- AI Classification -->
                        <div class="card detail-section">
                            <div class="detail-section-title">AI Classification</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                <div class="detail-field">
                                    <div class="detail-field-label">Category</div>
                                    <div class="detail-field-value">${Utils.escapeHtml(Utils.shortCategory(c.system_category))}</div>
                                    ${categoryOverridden ? `<div class="override-indicator">Overridden to: ${Utils.escapeHtml(Utils.shortCategory(c.manual_category))}</div>` : ''}
                                </div>
                                <div class="detail-field">
                                    <div class="detail-field-label">Subcategory</div>
                                    <div class="detail-field-value">${Utils.escapeHtml(c.system_subcategory || '—')}</div>
                                </div>
                            </div>
                            <div class="detail-field">
                                <div class="detail-field-label">Confidence</div>
                                <div class="confidence-bar">
                                    <div class="confidence-track">
                                        <div class="confidence-fill ${confidenceLevel}" style="width: ${confidencePct}%"></div>
                                    </div>
                                    <span style="font-weight: 600; min-width: 45px;">${confidencePct}%</span>
                                </div>
                                ${c.needs_human_review ? '<div style="margin-top: 0.5rem; font-size: 0.75rem; color: #f59e0b;">⚠ Below confidence threshold — manual review recommended</div>' : ''}
                            </div>
                        </div>

                        <!-- Priority -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Priority Assessment</div>
                            <div class="detail-field">
                                <div class="detail-field-label">System Priority</div>
                                <div class="detail-field-value">${Utils.priorityBadge(c.system_priority)}</div>
                                ${priorityOverridden ? `<div class="override-indicator">Manually changed to: ${Utils.priorityBadge(c.manual_priority)}</div>` : ''}
                            </div>
                            ${c.priority_explanation ? `
                                <div class="detail-field">
                                    <div class="detail-field-label">Why</div>
                                    <div class="priority-explanation">${Utils.escapeHtml(c.priority_explanation)}</div>
                                </div>
                            ` : ''}
                        </div>

                        <!-- Internal Notes -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Internal Notes</div>
                            <div class="notes-list" id="notes-list">
                                ${(c.internal_notes || []).length === 0
                                    ? '<p style="color: var(--color-secondary-text); font-size: 0.875rem;">No notes yet.</p>'
                                    : (c.internal_notes || []).map(n => `
                                        <div class="note-item">
                                            <div class="note-header">
                                                <span class="note-author">${Utils.escapeHtml(n.author_name || 'Unknown')}</span>
                                                <span class="note-date">${Utils.formatDateTime(n.created_at)}</span>
                                            </div>
                                            <div class="note-content">${Utils.escapeHtml(n.content)}</div>
                                        </div>
                                    `).join('')
                                }
                            </div>
                            <form id="add-note-form" style="margin-top: 1rem;">
                                <div class="form-group" style="margin-bottom: 0.5rem;">
                                    <textarea id="note-content" class="form-textarea" placeholder="Add an internal note..."
                                              style="min-height: 80px;"></textarea>
                                </div>
                                <button type="submit" class="btn btn-secondary btn-sm">Add Note</button>
                            </form>
                        </div>

                        <!-- Status History -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Status History</div>
                            <div class="timeline">
                                ${(c.status_history || []).map(h => `
                                    <div class="timeline-item completed">
                                        <div class="timeline-title">${Utils.statusLabel(h.new_status)}${h.old_status ? ` (from ${Utils.statusLabel(h.old_status)})` : ''}</div>
                                        <div class="timeline-date">
                                            ${Utils.formatDateTime(h.created_at)} — ${Utils.escapeHtml(h.changed_by_name || 'System')}
                                            ${h.reason ? `<br><em style="color: var(--color-secondary-text);">${Utils.escapeHtml(h.reason)}</em>` : ''}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>

                    <!-- Right column: Actions -->
                    <div>
                        <!-- Quick Actions -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Actions</div>

                            <!-- Status Change -->
                            <div class="form-group">
                                <label class="form-label" for="action-status">Change Status</label>
                                <select id="action-status" class="form-select">
                                    <option value="">Select status...</option>
                                    <option value="submitted">Submitted</option>
                                    <option value="under_review">Under Review</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="waiting_for_customer">Waiting for Customer</option>
                                    <option value="resolved">Resolved</option>
                                    <option value="closed">Closed</option>
                                </select>
                            </div>
                            <button class="btn btn-primary btn-sm btn-block" id="btn-update-status"
                                    onclick="SupportPortal._updateStatus('${c.id}')">
                                Update Status
                            </button>

                            ${canEditPriority ? `
                                <hr style="border: none; border-top: 1px solid var(--color-border); margin: 1.25rem 0;">

                                <!-- Priority Override -->
                                <div class="form-group">
                                    <label class="form-label" for="action-priority">Override Priority</label>
                                    <select id="action-priority" class="form-select">
                                        <option value="">Select priority...</option>
                                        <option value="critical">Critical</option>
                                        <option value="high">High</option>
                                        <option value="medium">Medium</option>
                                        <option value="low">Low</option>
                                    </select>
                                </div>
                                <button class="btn btn-secondary btn-sm btn-block" id="btn-override-priority"
                                        onclick="SupportPortal._overridePriority('${c.id}')">
                                    Override Priority
                                </button>
                            ` : ''}

                            ${canAssign ? `
                                <hr style="border: none; border-top: 1px solid var(--color-border); margin: 1.25rem 0;">

                                <!-- Assignment -->
                                <div class="form-group">
                                    <label class="form-label" for="action-assign">Assign To</label>
                                    <select id="action-assign" class="form-select">
                                        <option value="">Select agent...</option>
                                    </select>
                                </div>
                                <button class="btn btn-secondary btn-sm btn-block" id="btn-assign"
                                        onclick="SupportPortal._assignComplaint('${c.id}')">
                                    Assign
                                </button>
                            ` : ''}

                            <hr style="border: none; border-top: 1px solid var(--color-border); margin: 1.25rem 0;">

                            <!-- Resolve / Reopen -->
                            ${c.status !== 'resolved' && c.status !== 'closed' ? `
                                <button class="btn btn-success btn-sm btn-block" onclick="SupportPortal._resolveComplaint('${c.id}')">
                                    ✓ Resolve Complaint
                                </button>
                            ` : `
                                ${canEditPriority ? `
                                    <button class="btn btn-secondary btn-sm btn-block" onclick="SupportPortal._reopenComplaint('${c.id}')">
                                        ↩ Reopen Complaint
                                    </button>
                                ` : ''}
                            `}
                        </div>

                        <!-- Assignment Info -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Assignment</div>
                            <div class="detail-field">
                                <div class="detail-field-label">Team</div>
                                <div class="detail-field-value">${Utils.escapeHtml(c.assigned_team || 'Unassigned')}</div>
                            </div>
                            <div class="detail-field">
                                <div class="detail-field-label">Agent</div>
                                <div class="detail-field-value">${Utils.escapeHtml(c.assignee_name || 'Unassigned')}</div>
                            </div>
                        </div>

                        <!-- Metadata -->
                        <div class="card detail-section">
                            <div class="detail-section-title">Metadata</div>
                            <div class="detail-field">
                                <div class="detail-field-label">Created</div>
                                <div class="detail-field-value" style="font-size: 0.875rem;">${Utils.formatDateTime(c.created_at)}</div>
                            </div>
                            <div class="detail-field">
                                <div class="detail-field-label">Updated</div>
                                <div class="detail-field-value" style="font-size: 0.875rem;">${Utils.formatDateTime(c.updated_at)}</div>
                            </div>
                            <div class="detail-field">
                                <div class="detail-field-label">Model Version</div>
                                <div class="detail-field-value" style="font-size: 0.75rem; font-family: monospace;">${Utils.escapeHtml(c.model_version || '—')}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Load agents for assignment dropdown
        if (canAssign) {
            this._loadAgentDropdown();
        }

        // Note form handler
        document.getElementById('add-note-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const content = document.getElementById('note-content').value.trim();
            if (!content) return;

            try {
                const note = await API.addNote(c.id, content);
                document.getElementById('note-content').value = '';
                Utils.showToast('Note added', 'success');
                // Refresh
                this.renderComplaintDetail(c.id);
            } catch (error) {
                Utils.showToast(error.error || 'Failed to add note', 'error');
            }
        });
    },

    async _loadAgentDropdown() {
        try {
            const data = await API.listAgents();
            const select = document.getElementById('action-assign');
            if (!select) return;
            (data.agents || []).forEach(agent => {
                const opt = document.createElement('option');
                opt.value = agent.id;
                opt.textContent = `${agent.display_name} (${agent.role})`;
                select.appendChild(opt);
            });
        } catch (e) {
            // Silently fail
        }
    },

    async _updateStatus(id) {
        const status = document.getElementById('action-status').value;
        if (!status) {
            Utils.showToast('Please select a status', 'info');
            return;
        }
        try {
            await API.updateComplaint(id, { status });
            Utils.showToast('Status updated', 'success');
            this.renderComplaintDetail(id);
        } catch (error) {
            Utils.showToast(error.error || 'Failed to update status', 'error');
        }
    },

    async _overridePriority(id) {
        const priority = document.getElementById('action-priority').value;
        if (!priority) {
            Utils.showToast('Please select a priority', 'info');
            return;
        }
        try {
            await API.updateComplaint(id, { manual_priority: priority });
            Utils.showToast('Priority overridden', 'success');
            this.renderComplaintDetail(id);
        } catch (error) {
            Utils.showToast(error.error || 'Failed to override priority', 'error');
        }
    },

    async _assignComplaint(id) {
        const agentId = document.getElementById('action-assign').value;
        if (!agentId) {
            Utils.showToast('Please select an agent', 'info');
            return;
        }
        try {
            await API.assignComplaint(id, { assigned_to: agentId });
            Utils.showToast('Complaint assigned', 'success');
            this.renderComplaintDetail(id);
        } catch (error) {
            Utils.showToast(error.error || 'Failed to assign complaint', 'error');
        }
    },

    async _resolveComplaint(id) {
        const note = prompt('Resolution note (optional):');
        try {
            await API.resolveComplaint(id, note || '');
            Utils.showToast('Complaint resolved', 'success');
            this.renderComplaintDetail(id);
        } catch (error) {
            Utils.showToast(error.error || 'Failed to resolve complaint', 'error');
        }
    },

    async _reopenComplaint(id) {
        const reason = prompt('Reason for reopening (optional):');
        try {
            await API.reopenComplaint(id, reason || '');
            Utils.showToast('Complaint reopened', 'success');
            this.renderComplaintDetail(id);
        } catch (error) {
            Utils.showToast(error.error || 'Failed to reopen complaint', 'error');
        }
    },

    // ==================== Analytics ====================

    async renderAnalytics() {
        if (!this.requireAuth()) return;
        this.renderNav();
        // Reuse dashboard for now
        this.renderDashboard();
    },

    // ==================== Settings ====================

    renderSettings() {
        if (!this.requireAuth()) return;
        this.renderNav();
        const main = document.getElementById('main-content');
        const user = API.getUser();

        if (user.role !== 'admin') {
            main.innerHTML = `
                <div class="page-container narrow page-enter">
                    <div class="empty-state">
                        <div class="empty-icon">🔒</div>
                        <h3>Access Denied</h3>
                        <p>Only administrators can access settings.</p>
                    </div>
                </div>
            `;
            return;
        }

        main.innerHTML = `
            <div class="page-container narrow page-enter">
                <div class="page-header">
                    <h1>System Settings</h1>
                </div>

                <div class="card detail-section">
                    <div class="detail-section-title">Configuration</div>
                    <p style="color: var(--color-secondary-text); font-size: 0.875rem;">
                        Priority rules and category configuration are managed via JSON files in the
                        <code>config/</code> directory. Restart the server after making changes.
                    </p>
                    <br>
                    <div class="detail-field">
                        <div class="detail-field-label">Priority Rules</div>
                        <div class="detail-field-value" style="font-family: monospace; font-size: 0.875rem;">config/priority_rules.json</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Categories</div>
                        <div class="detail-field-value" style="font-family: monospace; font-size: 0.875rem;">config/categories.json</div>
                    </div>
                    <div class="detail-field">
                        <div class="detail-field-label">Confidence Threshold</div>
                        <div class="detail-field-value">60%</div>
                    </div>
                </div>

                <div class="card detail-section">
                    <div class="detail-section-title">Model Management</div>
                    <p style="color: var(--color-secondary-text); font-size: 0.875rem;">
                        To retrain the classifier, run:<br>
                        <code style="background: var(--color-background); padding: 0.5rem 0.75rem; border-radius: 0.375rem; display: inline-block; margin-top: 0.5rem;">
                            python -m ml.train
                        </code>
                    </p>
                </div>
            </div>
        `;
    },
};
