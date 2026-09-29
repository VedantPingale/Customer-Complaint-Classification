"""Support staff API routes.

All endpoints require authentication.
Role-based access control is enforced at the route level.
"""

import json
from flask import Blueprint, request, jsonify, g
from backend.auth import (
    login_required, role_required, admin_required,
    manager_or_admin_required, verify_password, create_token
)
from backend.models import db, SupportUser, Complaint
from backend.services.complaint_service import ComplaintService

support_bp = Blueprint("support", __name__, url_prefix="/api/support")


@support_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a support staff user.

    Request body:
        username: str
        password: str

    Returns:
        token: str - JWT token
        user: dict - User profile
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = SupportUser.query.filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is inactive"}), 403

    token = create_token(user.id, user.username, user.role)

    return jsonify({
        "token": token,
        "user": user.to_dict(),
    }), 200


@support_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """Get the current authenticated user's profile."""
    return jsonify({"user": g.current_user.to_dict()}), 200


@support_bp.route("/complaints", methods=["GET"])
@login_required
def list_complaints():
    """List complaints with filtering and sorting.

    Query parameters:
        priority: str
        category: str
        status: str
        assigned_team: str
        assigned_to: str
        needs_human_review: bool
        search: str
    """
    user = g.current_user

    filters = {
        "priority": request.args.get("priority"),
        "category": request.args.get("category"),
        "status": request.args.get("status"),
        "assigned_team": request.args.get("assigned_team"),
        "assigned_to": request.args.get("assigned_to"),
        "needs_human_review": request.args.get("needs_human_review"),
        "search": request.args.get("search"),
    }

    # Agents can only see their assigned complaints
    if user.role == "agent":
        filters["assigned_to"] = user.id

    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    complaints = ComplaintService.list_support_complaints(filters)
    return jsonify({"complaints": complaints, "total": len(complaints)}), 200


@support_bp.route("/complaints/<complaint_id>", methods=["GET"])
@login_required
def get_complaint(complaint_id):
    """Get detailed complaint information for support staff."""
    user = g.current_user
    result = ComplaintService.get_support_complaint(complaint_id)

    if not result:
        return jsonify({"error": "Complaint not found"}), 404

    # Agents can only view their assigned complaints
    if user.role == "agent" and result.get("assigned_to") != user.id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify(result), 200


@support_bp.route("/complaints/<complaint_id>", methods=["PATCH"])
@login_required
def update_complaint(complaint_id):
    """Update complaint fields.

    Request body (all optional):
        status: str
        manual_category: str
        manual_subcategory: str
        manual_priority: str
        needs_human_review: bool
        reason: str
    """
    user = g.current_user
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Agents can only update their assigned complaints
    if user.role == "agent":
        complaint = Complaint.query.get(complaint_id)
        if not complaint or complaint.assigned_to != user.id:
            return jsonify({"error": "Access denied"}), 403

    result = ComplaintService.update_complaint(
        complaint_id, data, user.id, user.display_name, user.role
    )

    if not result:
        return jsonify({"error": "Complaint not found"}), 404

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200


@support_bp.route("/complaints/<complaint_id>/notes", methods=["POST"])
@login_required
def add_note(complaint_id):
    """Add an internal note to a complaint.

    Request body:
        content: str
    """
    user = g.current_user
    data = request.get_json()

    if not data or not data.get("content", "").strip():
        return jsonify({"error": "Note content is required"}), 400

    # Agents can only add notes to their assigned complaints
    if user.role == "agent":
        complaint = Complaint.query.get(complaint_id)
        if not complaint or complaint.assigned_to != user.id:
            return jsonify({"error": "Access denied"}), 403

    result = ComplaintService.add_internal_note(
        complaint_id, data["content"], user.id
    )

    if not result:
        return jsonify({"error": "Complaint not found"}), 404

    return jsonify(result), 201


@support_bp.route("/complaints/<complaint_id>/assign", methods=["POST"])
@role_required("admin", "manager")
def assign_complaint(complaint_id):
    """Assign a complaint to an agent or team.

    Request body:
        assigned_to: str (user ID, optional)
        team: str (optional)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    result = ComplaintService.assign_complaint(
        complaint_id,
        assigned_to=data.get("assigned_to"),
        team=data.get("team"),
        assigner_id=g.current_user.id,
        assigner_name=g.current_user.display_name,
    )

    if not result:
        return jsonify({"error": "Complaint not found"}), 404

    return jsonify(result), 200


@support_bp.route("/complaints/<complaint_id>/resolve", methods=["POST"])
@login_required
def resolve_complaint(complaint_id):
    """Mark a complaint as resolved.

    Request body:
        resolution_note: str (optional)
    """
    user = g.current_user
    data = request.get_json() or {}

    # Agents can only resolve their assigned complaints
    if user.role == "agent":
        complaint = Complaint.query.get(complaint_id)
        if not complaint or complaint.assigned_to != user.id:
            return jsonify({"error": "Access denied"}), 403

    result = ComplaintService.resolve_complaint(
        complaint_id, user.id, user.display_name,
        data.get("resolution_note")
    )

    if not result:
        return jsonify({"error": "Complaint not found"}), 404

    return jsonify(result), 200


@support_bp.route("/complaints/<complaint_id>/reopen", methods=["POST"])
@role_required("admin", "manager")
def reopen_complaint(complaint_id):
    """Reopen a resolved or closed complaint.

    Request body:
        reason: str (optional)
    """
    data = request.get_json() or {}

    result = ComplaintService.reopen_complaint(
        complaint_id, g.current_user.id, g.current_user.display_name,
        data.get("reason")
    )

    if not result:
        return jsonify({"error": "Complaint not found"}), 404

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200


@support_bp.route("/agents", methods=["GET"])
@login_required
def list_agents():
    """List all support agents (for assignment dropdowns)."""
    agents = SupportUser.query.filter_by(is_active=True).all()
    return jsonify({"agents": [a.to_dict() for a in agents]}), 200


@support_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """List all support users (admin only)."""
    users = SupportUser.query.all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200


@support_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    """Create a new support user (admin only).

    Request body:
        username: str
        email: str
        password: str
        role: str
        display_name: str
    """
    from backend.auth import hash_password
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required = ["username", "email", "password", "role", "display_name"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    if data["role"] not in ("admin", "manager", "agent"):
        return jsonify({"error": "Invalid role"}), 400

    # Check uniqueness
    if SupportUser.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409
    if SupportUser.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    user = SupportUser(
        username=data["username"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
        role=data["role"],
        display_name=data["display_name"],
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"user": user.to_dict()}), 201
