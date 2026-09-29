"""Flask application factory and main entry point."""

import os
import logging
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.config import get_config
from backend.models import db
from backend.routes.customer import customer_bp
from backend.routes.support import support_bp
from backend.routes.analytics import analytics_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"),
        static_url_path="",
    )

    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object(get_config())

    # Enable CORS for development
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize database
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(customer_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(analytics_bp)

    # Initialize classifier and priority engine
    with app.app_context():
        from backend.services.classifier import get_classifier
        from backend.services.priority_engine import get_priority_engine
        get_classifier(app.config)
        get_priority_engine(app.config.get("PRIORITY_RULES_PATH"))

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        # If it's an API request, return JSON
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"error": "Resource not found"}), 404
        # Otherwise serve the frontend
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(500)
    def internal_error(error):
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    # Health check endpoint
    @app.route("/api/health")
    def health_check():
        return jsonify({"status": "ok", "version": "1.0.0"}), 200

    # Serve the SPA - catch all routes for frontend
    @app.route("/")
    @app.route("/customer")
    @app.route("/customer/<path:path>")
    @app.route("/support")
    @app.route("/support/<path:path>")
    def serve_spa(path=None):
        return send_from_directory(app.static_folder, "index.html")

    # Create database tables
    with app.app_context():
        db.create_all()

        # Seed demo data in development
        if app.config.get("DEBUG") or app.config.get("TESTING"):
            from backend.seed_data import seed_database
            try:
                from backend.models import SupportUser
                if SupportUser.query.count() == 0:
                    seed_database(app.config)
            except Exception as e:
                logger.warning("Seed data creation failed: %s", e)

    return app
