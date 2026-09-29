"""Customer-facing API routes.

All endpoints return only customer-safe data.
No internal model metadata, priority scores, or staff notes are exposed.
"""

from flask import Blueprint, request, jsonify
from backend.services.complaint_service import ComplaintService
from backend.utils.sanitizer import validate_complaint_input

customer_bp = Blueprint("customer", __name__, url_prefix="/api/customer")


@customer_bp.route("/complaints", methods=["POST"])
def submit_complaint():
    """Submit a new customer complaint.

    Request body:
        name: str (required)
        email: str (required)
        description: str (required)
        product_type: str (optional)

    Returns:
        reference: str - Complaint reference number
        status: str
        message: str
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Validate input
    errors = validate_complaint_input(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        from flask import current_app
        result = ComplaintService.create_complaint(data, current_app.config)
        return jsonify(result), 201
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Complaint creation failed: %s", str(e))
        return jsonify({"error": "Unable to process your complaint. Please try again."}), 500


@customer_bp.route("/complaints/<reference>", methods=["GET"])
def track_complaint(reference):
    """Track a complaint by reference number.

    Returns only customer-safe information:
    - Reference number
    - Status
    - Status timeline
    - Customer notifications
    """
    if not reference or not reference.strip():
        return jsonify({"error": "Reference number is required"}), 400

    result = ComplaintService.get_customer_complaint(reference)
    if not result:
        return jsonify({"error": "Complaint not found. Please check your reference number."}), 404

    return jsonify(result), 200
