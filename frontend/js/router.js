/* ==========================================================================
   Client-Side Router
   ========================================================================== */

const Router = {
    routes: [],
    currentPath: '',

    /**
     * Register a route.
     */
    on(path, handler) {
        this.routes.push({
            path,
            regex: this._pathToRegex(path),
            handler,
        });
    },

    /**
     * Convert a path pattern to a regex.
     */
    _pathToRegex(path) {
        const pattern = path
            .replace(/\//g, '\\/')
            .replace(/:([^/]+)/g, '(?<$1>[^/]+)');
        return new RegExp(`^${pattern}$`);
    },

    /**
     * Navigate to a path.
     */
    navigate(path) {
        window.history.pushState({}, '', path);
        this._resolve();
    },

    /**
     * Resolve the current path against registered routes.
     */
    _resolve() {
        const path = window.location.pathname;
        this.currentPath = path;

        for (const route of this.routes) {
            const match = path.match(route.regex);
            if (match) {
                const params = match.groups || {};
                route.handler(params);
                return;
            }
        }

        // 404 fallback
        this._notFound();
    },

    /**
     * Handle 404.
     */
    _notFound() {
        const main = document.getElementById('main-content');
        main.innerHTML = `
            <div class="page-container narrow page-enter">
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <h3>Page Not Found</h3>
                    <p>The page you're looking for doesn't exist.</p>
                    <br>
                    <a href="/" class="btn btn-primary" onclick="event.preventDefault(); Router.navigate('/')">Go Home</a>
                </div>
            </div>
        `;
    },

    /**
     * Initialize the router.
     */
    init() {
        // Handle browser back/forward
        window.addEventListener('popstate', () => this._resolve());

        // Handle link clicks
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (!link) return;

            const href = link.getAttribute('href');
            if (!href || href.startsWith('http') || href.startsWith('#') || href.startsWith('mailto:')) return;

            e.preventDefault();
            this.navigate(href);
        });

        // Resolve initial path
        this._resolve();
    },
};
