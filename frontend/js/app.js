/* ==========================================================================
   Application Entry Point - Route Registration
   ========================================================================== */

(function () {
    'use strict';

    // ==================== Route Registration ====================

    // Landing page
    Router.on('/', () => {
        const navbar = document.getElementById('navbar');
        document.body.classList.remove('theme-light');

        navbar.innerHTML = `
            <a href="/" class="navbar-brand">
                <div class="brand-icon">🛡️</div>
                <span>Complaint Manager</span>
            </a>
        `;

        const main = document.getElementById('main-content');
        main.innerHTML = `
            <div class="page-enter">
                <div class="hero">
                    <h1>Customer Complaint<br>Management System</h1>
                    <p>An intelligent platform that automatically classifies, prioritizes, and routes customer complaints for fast resolution.</p>
                </div>
                <div class="landing-cards">
                    <div class="card landing-card" onclick="Router.navigate('/customer')">
                        <div class="card-icon">👤</div>
                        <h3>Customer Portal</h3>
                        <p>Submit a complaint or track the status of an existing complaint.</p>
                    </div>
                    <div class="card landing-card" onclick="Router.navigate('/support/login')">
                        <div class="card-icon">🔧</div>
                        <h3>Support Portal</h3>
                        <p>Internal dashboard for managing, classifying, and resolving complaints.</p>
                    </div>
                </div>
            </div>
        `;
    });

    // ==================== Customer Routes ====================
    Router.on('/customer', () => CustomerPortal.renderHome());
    Router.on('/customer/submit', () => CustomerPortal.renderSubmitForm());
    Router.on('/customer/track', () => CustomerPortal.renderTrack());
    Router.on('/customer/complaints/:reference', (params) => CustomerPortal.renderComplaintDetail(params.reference));

    // ==================== Support Routes ====================
    Router.on('/support', () => SupportPortal.renderDashboard());
    Router.on('/support/login', () => SupportPortal.renderLogin());
    Router.on('/support/complaints', () => SupportPortal.renderQueue());
    Router.on('/support/complaints/:id', (params) => SupportPortal.renderComplaintDetail(params.id));
    Router.on('/support/analytics', () => SupportPortal.renderAnalytics());
    Router.on('/support/settings', () => SupportPortal.renderSettings());

    // ==================== Initialize ====================
    Router.init();
})();
