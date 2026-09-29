"""Analytics API routes for support dashboard."""

from flask import Blueprint, jsonify
from backend.auth import login_required, role_required
from backend.services.complaint_service import ComplaintService

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/support/analytics")


@analytics_bp.route("/overview", methods=["GET"])
@login_required
def overview():
    """Get analytics overview with summary statistics."""
    try:
        data = ComplaintService.get_analytics_overview()
        return jsonify(data), 200
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Analytics error: %s", str(e))
        return jsonify({"error": "Failed to load analytics"}), 500


@analytics_bp.route("/categories", methods=["GET"])
@login_required
def categories():
    """Get complaint distribution by category."""
    data = ComplaintService.get_analytics_overview()
    return jsonify({"by_category": data.get("by_category", [])}), 200


@analytics_bp.route("/priorities", methods=["GET"])
@login_required
def priorities():
    """Get complaint distribution by priority."""
    data = ComplaintService.get_analytics_overview()
    return jsonify({"by_priority": data.get("by_priority", {})}), 200
