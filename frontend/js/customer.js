/* ==========================================================================
   Customer Portal
   ========================================================================== */

const CustomerPortal = {
    /**
     * Render the customer navigation bar.
     */
    renderNav() {
        const navbar = document.getElementById('navbar');
        const path = window.location.pathname;

        navbar.innerHTML = `
            <a href="/customer" class="navbar-brand" onclick="event.preventDefault(); Router.navigate('/customer')">
                <div class="brand-icon">🛡️</div>
                <span>Customer Support</span>
            </a>
            <ul class="navbar-nav" id="customer-nav-menu">
                <li><a href="/customer" class="${path === '/customer' ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/customer')">🏠 Home</a></li>
                <li><a href="/customer/submit" class="${path === '/customer/submit' ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/customer/submit')">📝 Submit Complaint</a></li>
                <li><a href="/customer/track" class="${path.startsWith('/customer/track') || path.startsWith('/customer/complaints') ? 'active' : ''}"
                    onclick="event.preventDefault(); Router.navigate('/customer/track')">🔍 Track Complaint</a></li>
            </ul>
            <button class="navbar-toggle" id="customer-nav-toggle" aria-label="Toggle navigation">☰</button>
        `;

        // Mobile toggle
        document.getElementById('customer-nav-toggle').addEventListener('click', () => {
            document.getElementById('customer-nav-menu').classList.toggle('show');
        });

        // Apply light theme for customer portal
        document.body.classList.add('theme-light');
    },

    /**
     * Customer Home Page
     */
    renderHome() {
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-enter">
                <div class="hero">
                    <h1>How can we help you?</h1>
                    <p>We're here to listen and resolve your concerns. Submit a complaint or track an existing one — we'll take care of the rest.</p>
                    <div class="hero-actions">
                        <a href="/customer/submit" class="btn btn-primary btn-lg"
                           onclick="event.preventDefault(); Router.navigate('/customer/submit')">
                            📝 Submit a Complaint
                        </a>
                        <a href="/customer/track" class="btn btn-secondary btn-lg"
                           onclick="event.preventDefault(); Router.navigate('/customer/track')">
                            🔍 Track Your Complaint
                        </a>
                    </div>
                </div>

                <div class="landing-cards">
                    <div class="card landing-card" onclick="Router.navigate('/customer/submit')">
                        <div class="card-icon">📝</div>
                        <h3>Submit a Complaint</h3>
                        <p>Tell us about your issue and we'll assign it to the right team immediately.</p>
                    </div>
                    <div class="card landing-card" onclick="Router.navigate('/customer/track')">
                        <div class="card-icon">🔍</div>
                        <h3>Track Your Complaint</h3>
                        <p>Already submitted? Enter your reference number to check the current status.</p>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Complaint Submission Form
     */
    renderSubmitForm() {
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container narrow page-enter">
                <div class="page-header">
                    <div class="breadcrumbs">
                        <a href="/customer" onclick="event.preventDefault(); Router.navigate('/customer')">Home</a>
                        <span class="separator">›</span>
                        <span>Submit Complaint</span>
                    </div>
                    <h1>Submit a Complaint</h1>
                </div>

                <div class="card" id="submit-form-card">
                    <form id="complaint-form" novalidate>
                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="complaint-name">
                                    Full Name <span class="required">*</span>
                                </label>
                                <input type="text" id="complaint-name" class="form-input"
                                       placeholder="Your full name" required maxlength="200" autocomplete="name">
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="complaint-email">
                                    Email Address <span class="required">*</span>
                                </label>
                                <input type="email" id="complaint-email" class="form-input"
                                       placeholder="your@email.com" required autocomplete="email">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="complaint-description">
                                Describe Your Issue <span class="required">*</span>
                            </label>
                            <textarea id="complaint-description" class="form-textarea"
                                      placeholder="Please describe your issue in detail. Include relevant dates, amounts, and any reference numbers you may have."
                                      required minlength="20" maxlength="10000"></textarea>
                            <div class="form-hint">Minimum 20 characters. Be as detailed as possible.</div>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="complaint-product">
                                Product/Service Type <span style="color: var(--color-secondary-text)">(optional)</span>
                            </label>
                            <select id="complaint-product" class="form-select">
                                <option value="">Select if applicable...</option>
                                <option value="credit_card">Credit Card</option>
                                <option value="bank_account">Bank Account</option>
                                <option value="mortgage">Mortgage</option>
                                <option value="student_loan">Student Loan</option>
                                <option value="auto_loan">Auto/Vehicle Loan</option>
                                <option value="personal_loan">Personal Loan</option>
                                <option value="credit_report">Credit Report</option>
                                <option value="debt_collection">Debt Collection</option>
                                <option value="money_transfer">Money Transfer</option>
                                <option value="other">Other</option>
                            </select>
                        </div>

                        <div id="form-errors" style="display:none; margin-bottom: 1rem;">
                            <div class="form-error" id="form-error-text"></div>
                        </div>

                        <button type="submit" id="submit-btn" class="btn btn-primary btn-lg btn-block">
                            Submit Complaint
                        </button>
                    </form>
                </div>
            </div>
        `;

        // Handle form submission
        document.getElementById('complaint-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit();
        });
    },

    /**
     * Handle complaint form submission.
     */
    async handleSubmit() {
        const btn = document.getElementById('submit-btn');
        const errorsDiv = document.getElementById('form-errors');
        const errorText = document.getElementById('form-error-text');

        const name = document.getElementById('complaint-name').value.trim();
        const email = document.getElementById('complaint-email').value.trim();
        const description = document.getElementById('complaint-description').value.trim();
        const product = document.getElementById('complaint-product').value;

        // Client-side validation
        const errors = [];
        if (!name) errors.push('Please enter your name.');
        if (!email) errors.push('Please enter your email.');
        if (!description) errors.push('Please describe your issue.');
        else if (description.length < 20) errors.push('Please provide more detail (at least 20 characters).');

        if (errors.length > 0) {
            errorsDiv.style.display = 'block';
            errorText.textContent = errors.join(' ');
            return;
        }

        errorsDiv.style.display = 'none';
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner spinner-inline"></div> Submitting...';

        try {
            const result = await API.submitComplaint({
                name,
                email,
                description,
                product_type: product || undefined,
            });

            this.renderSuccess(result.reference);
        } catch (error) {
            const msg = error.errors ? error.errors.join(' ') : (error.error || 'Something went wrong. Please try again.');
            errorsDiv.style.display = 'block';
            errorText.textContent = msg;
            btn.disabled = false;
            btn.textContent = 'Submit Complaint';
        }
    },

    /**
     * Render the success screen after submission.
     */
    renderSuccess(reference) {
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container narrow page-enter">
                <div class="card">
                    <div class="success-screen">
                        <div class="success-icon">✓</div>
                        <h2>Complaint Submitted Successfully</h2>
                        <p style="color: var(--color-secondary-text); margin-bottom: 1rem;">
                            Your complaint has been received and is being processed by our team.
                        </p>

                        <div style="margin-bottom: 0.5rem; font-size: 0.875rem; color: var(--color-secondary-text);">
                            Reference Number
                        </div>
                        <div class="reference-number">${Utils.escapeHtml(reference)}</div>

                        <p style="color: var(--color-secondary-text); font-size: 0.875rem; margin-top: 1rem; margin-bottom: 2rem;">
                            Save this number to track the status of your complaint.
                        </p>

                        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                            <a href="/customer/track" class="btn btn-primary"
                               onclick="event.preventDefault(); Router.navigate('/customer/track')">
                                🔍 Track Your Complaint
                            </a>
                            <a href="/customer/submit" class="btn btn-secondary"
                               onclick="event.preventDefault(); Router.navigate('/customer/submit')">
                                📝 Submit Another
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Complaint Tracking Page
     */
    renderTrack() {
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container narrow page-enter">
                <div class="page-header">
                    <div class="breadcrumbs">
                        <a href="/customer" onclick="event.preventDefault(); Router.navigate('/customer')">Home</a>
                        <span class="separator">›</span>
                        <span>Track Complaint</span>
                    </div>
                    <h1>Track Your Complaint</h1>
                </div>

                <div class="card">
                    <form id="track-form">
                        <div class="form-group">
                            <label class="form-label" for="track-reference">
                                Complaint Reference Number
                            </label>
                            <input type="text" id="track-reference" class="form-input"
                                   placeholder="CMP-2026-XXXXX" required
                                   style="text-transform: uppercase; letter-spacing: 0.05em; font-family: 'Courier New', monospace; font-size: 1.125rem;">
                        </div>

                        <div id="track-errors" style="display:none; margin-bottom: 1rem;">
                            <div class="form-error" id="track-error-text"></div>
                        </div>

                        <button type="submit" id="track-btn" class="btn btn-primary btn-lg btn-block">
                            Check Status
                        </button>
                    </form>
                </div>

                <div id="track-result" style="margin-top: 1.5rem;"></div>
            </div>
        `;

        document.getElementById('track-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleTrack();
        });
    },

    /**
     * Handle tracking form submission.
     */
    async handleTrack() {
        const reference = document.getElementById('track-reference').value.trim();
        const btn = document.getElementById('track-btn');
        const errorsDiv = document.getElementById('track-errors');
        const errorText = document.getElementById('track-error-text');
        const resultDiv = document.getElementById('track-result');

        if (!reference) {
            errorsDiv.style.display = 'block';
            errorText.textContent = 'Please enter your reference number.';
            return;
        }

        errorsDiv.style.display = 'none';
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner spinner-inline"></div> Checking...';

        try {
            const data = await API.trackComplaint(reference);
            this.renderTrackResult(data, resultDiv);
        } catch (error) {
            errorsDiv.style.display = 'block';
            errorText.textContent = error.error || 'Complaint not found. Please check your reference number.';
            resultDiv.innerHTML = '';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Check Status';
        }
    },

    /**
     * Render tracking result.
     */
    renderTrackResult(data, container) {
        const allStatuses = ['Submitted', 'Under Review', 'In Progress', 'Waiting for Customer', 'Resolved', 'Closed'];
        const currentLabel = data.status_label || Utils.statusLabel(data.status);

        // Find current status index
        const currentIdx = allStatuses.findIndex(s => s === currentLabel);

        let timelineHtml = '';
        allStatuses.forEach((status, idx) => {
            let cls = 'pending';
            if (idx < currentIdx) cls = 'completed';
            else if (idx === currentIdx) cls = 'current';

            // Find matching timeline entry
            const entry = (data.timeline || []).find(t => t.status === status);

            timelineHtml += `
                <div class="timeline-item ${cls}">
                    <div class="timeline-title">${Utils.escapeHtml(status)}</div>
                    ${entry ? `<div class="timeline-date">${Utils.formatDate(entry.date)}</div>` : ''}
                </div>
            `;
        });

        // Latest notification
        const latestNotif = data.notifications && data.notifications.length > 0
            ? data.notifications[0]
            : null;

        container.innerHTML = `
            <div class="card page-enter">
                <div class="card-header">
                    <div>
                        <div class="card-title">Complaint ${Utils.escapeHtml(data.reference)}</div>
                        <div class="card-subtitle">Submitted on ${Utils.formatDate(data.created_at)}</div>
                    </div>
                    ${Utils.statusBadge(data.status)}
                </div>

                ${latestNotif ? `
                    <div style="background: #ccfbf1; border: 1px solid rgba(59,130,246,0.15); border-radius: 0.5rem; padding: 1rem; margin-bottom: 1.5rem;">
                        <div style="font-size: 0.875rem; font-weight: 600; color: var(--color-accent); margin-bottom: 0.25rem;">
                            Latest Update
                        </div>
                        <div style="font-size: 0.875rem; color: var(--color-secondary-text);">
                            ${Utils.escapeHtml(latestNotif.message)}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--color-secondary-text); margin-top: 0.5rem;">
                            ${Utils.formatDate(latestNotif.created_at)}
                        </div>
                    </div>
                ` : ''}

                <div class="detail-section-title">Status Timeline</div>
                <div class="timeline">
                    ${timelineHtml}
                </div>
            </div>
        `;
    },

    /**
     * Customer complaint detail page (by reference).
     */
    async renderComplaintDetail(reference) {
        this.renderNav();
        const main = document.getElementById('main-content');

        main.innerHTML = `
            <div class="page-container narrow">
                <div class="loading-screen">
                    <div class="spinner"></div>
                    <p>Loading complaint details...</p>
                </div>
            </div>
        `;

        try {
            const data = await API.trackComplaint(reference);
            const container = document.createElement('div');
            container.id = 'track-result';
            main.innerHTML = `
                <div class="page-container narrow page-enter">
                    <div class="page-header">
                        <div class="breadcrumbs">
                            <a href="/customer" onclick="event.preventDefault(); Router.navigate('/customer')">Home</a>
                            <span class="separator">›</span>
                            <a href="/customer/track" onclick="event.preventDefault(); Router.navigate('/customer/track')">Track</a>
                            <span class="separator">›</span>
                            <span>${Utils.escapeHtml(reference)}</span>
                        </div>
                        <h1>Complaint Status</h1>
                    </div>
                    <div id="track-result"></div>
                </div>
            `;
            this.renderTrackResult(data, document.getElementById('track-result'));
        } catch (error) {
            main.innerHTML = `
                <div class="page-container narrow page-enter">
                    <div class="empty-state">
                        <div class="empty-icon">❌</div>
                        <h3>Complaint Not Found</h3>
                        <p>${Utils.escapeHtml(error.error || 'Unable to find this complaint.')}</p>
                        <br>
                        <a href="/customer/track" class="btn btn-primary"
                           onclick="event.preventDefault(); Router.navigate('/customer/track')">Try Again</a>
                    </div>
                </div>
            `;
        }
    },
};
