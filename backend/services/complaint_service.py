"""Complaint business logic service.

Handles complaint creation, classification, prioritization, assignment,
status changes, and audit logging.
"""

import json
import logging
from backend.models import (
    db, Complaint, Customer, Classification, PriorityDecision,
    StatusHistory, Assignment, InternalNote, AuditLog, Notification
)
from backend.utils.reference_generator import generate_reference
from backend.utils.sanitizer import sanitize_text, sanitize_email, mask_sensitive_data
from backend.services.classifier import get_classifier
from backend.services.priority_engine import get_priority_engine

logger = logging.getLogger(__name__)


class ComplaintService:
    """Service layer for complaint operations."""

    # Customer-visible status labels
    STATUS_LABELS = {
        "submitted": "Submitted",
        "under_review": "Under Review",
        "in_progress": "In Progress",
        "waiting_for_customer": "Waiting for Customer",
        "resolved": "Resolved",
        "closed": "Closed",
    }

    # Valid status transitions
    STATUS_TRANSITIONS = {
        "submitted": ["under_review", "in_progress", "closed"],
        "under_review": ["in_progress", "waiting_for_customer", "resolved", "closed"],
        "in_progress": ["waiting_for_customer", "resolved", "under_review", "closed"],
        "waiting_for_customer": ["in_progress", "under_review", "resolved", "closed"],
        "resolved": ["closed", "in_progress"],  # Can reopen
        "closed": ["in_progress"],  # Can reopen
    }

    @staticmethod
    def create_complaint(data: dict, app_config: dict = None) -> dict:
        """Create a new complaint with automatic classification and prioritization.

        Args:
            data: dict with name, email, description, product_type (optional)
            app_config: Flask app config dict

        Returns:
            dict with reference number and customer-safe data
        """
        # Sanitize inputs
        name = sanitize_text(data["name"])
        email = sanitize_email(data["email"])
        description = sanitize_text(data["description"])
        product_type = sanitize_text(data.get("product_type", ""))

        # Find or create customer
        customer = Customer.query.filter_by(email=email).first()
        if not customer:
            customer = Customer(name=name, email=email)
            db.session.add(customer)
            db.session.flush()

        # Generate reference
        reference = generate_reference()

        # Create complaint record
        complaint = Complaint(
            reference=reference,
            customer_id=customer.id,
            customer_name=name,
            customer_email=email,
            description=description,
            product_type=product_type if product_type else None,
            status="submitted",
        )
        db.session.add(complaint)
        db.session.flush()

        # Classify the complaint
        classifier = get_classifier(app_config)
        classification = classifier.classify(description)

        complaint.system_category = classification["category"]
        complaint.system_subcategory = classification["subcategory"]
        complaint.system_confidence = classification["confidence"]
        complaint.model_version = classification["model_version"]
        complaint.current_category = classification["category"]
        complaint.current_subcategory = classification["subcategory"]

        # Determine if human review is needed
        threshold = float((app_config or {}).get("CONFIDENCE_THRESHOLD", 0.60))
        complaint.needs_human_review = classification["confidence"] < threshold

        # Record classification
        cls_record = Classification(
            complaint_id=complaint.id,
            category=classification["category"],
            subcategory=classification["subcategory"],
            confidence=classification["confidence"],
            model_version=classification["model_version"],
        )
        db.session.add(cls_record)

        # Calculate priority
        engine = get_priority_engine()
        priority_result = engine.calculate_priority(
            text=description,
            category=classification["category"],
            subcategory=classification["subcategory"],
            confidence=classification["confidence"],
        )

        complaint.system_priority = priority_result["priority"]
        complaint.current_priority = priority_result["priority"]
        complaint.priority_explanation = priority_result["explanation"]
        complaint.priority_signals = priority_result["signals"]

        # Record priority decision
        priority_record = PriorityDecision(
            complaint_id=complaint.id,
            priority=priority_result["priority"],
            score=priority_result["score"],
            explanation=priority_result["explanation"],
            signals=priority_result["signals"],
        )
        db.session.add(priority_record)

        # Auto-assign team based on category
        try:
            categories_path = (app_config or {}).get("CATEGORIES_PATH", "config/categories.json")
            import os
            if os.path.exists(categories_path):
                with open(categories_path, "r") as f:
                    cat_config = json.load(f)
                team_mapping = cat_config.get("category_team_mapping", {})
                assigned_team = team_mapping.get(classification["category"], "General Support")
                complaint.assigned_team = assigned_team
        except Exception as e:
            logger.warning("Failed to auto-assign team: %s", e)
            complaint.assigned_team = "General Support"

        # Record initial status
        status_record = StatusHistory(
            complaint_id=complaint.id,
            old_status=None,
            new_status="submitted",
            changed_by="system",
            changed_by_name="System",
            reason="Complaint submitted",
        )
        db.session.add(status_record)

        # Create customer notification
        notification = Notification(
            complaint_id=complaint.id,
            customer_id=customer.id,
            message=f"Your complaint has been submitted successfully. Reference: {reference}",
            notification_type="status_update",
        )
        db.session.add(notification)

        # Audit log
        audit = AuditLog(
            entity_type="complaint",
            entity_id=complaint.id,
            action="created",
            new_value=json.dumps({
                "reference": reference,
                "category": classification["category"],
                "priority": priority_result["priority"],
            }),
            user_id="system",
            user_name="System",
        )
        db.session.add(audit)

        db.session.commit()

        return {
            "reference": reference,
            "status": "submitted",
            "message": "Complaint submitted successfully.",
        }

    @staticmethod
    def get_customer_complaint(reference: str) -> dict:
        """Get customer-safe complaint data by reference number."""
        complaint = Complaint.query.filter_by(reference=reference.upper().strip()).first()
        if not complaint:
            return None

        # Get status timeline
        history = StatusHistory.query.filter_by(
            complaint_id=complaint.id
        ).order_by(StatusHistory.created_at.asc()).all()

        timeline = [
            {
                "status": ComplaintService.STATUS_LABELS.get(h.new_status, h.new_status),
                "date": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ]

        # Get customer-safe notifications
        notifications = Notification.query.filter_by(
            complaint_id=complaint.id
        ).order_by(Notification.created_at.desc()).limit(10).all()

        result = complaint.to_customer_dict()
        result["status_label"] = ComplaintService.STATUS_LABELS.get(
            complaint.status, complaint.status
        )
        result["timeline"] = timeline
        result["notifications"] = [n.to_dict() for n in notifications]

        return result

    @staticmethod
    def get_support_complaint(complaint_id: str) -> dict:
        """Get full internal complaint data for support staff."""
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return None

        result = complaint.to_support_dict()

        # Include history
        history = StatusHistory.query.filter_by(
            complaint_id=complaint.id
        ).order_by(StatusHistory.created_at.desc()).all()
        result["status_history"] = [h.to_dict() for h in history]

        # Include notes
        notes = InternalNote.query.filter_by(
            complaint_id=complaint.id
        ).order_by(InternalNote.created_at.desc()).all()
        result["internal_notes"] = [n.to_dict() for n in notes]

        # Include assignments
        assignments = Assignment.query.filter_by(
            complaint_id=complaint.id
        ).order_by(Assignment.assigned_at.desc()).all()
        result["assignment_history"] = [a.to_dict() for a in assignments]

        # Include classification history
        classifications = Classification.query.filter_by(
            complaint_id=complaint.id
        ).order_by(Classification.created_at.desc()).all()
        result["classification_history"] = [c.to_dict() for c in classifications]

        return result

    @staticmethod
    def list_support_complaints(filters: dict = None) -> list:
        """List complaints with filtering and sorting for support staff.

        Supports filters: priority, category, status, assigned_team,
        assigned_to, needs_human_review, search
        """
        query = Complaint.query

        if filters:
            if filters.get("priority"):
                query = query.filter(Complaint.current_priority == filters["priority"])
            if filters.get("category"):
                query = query.filter(Complaint.current_category == filters["category"])
            if filters.get("status"):
                query = query.filter(Complaint.status == filters["status"])
            if filters.get("assigned_team"):
                query = query.filter(Complaint.assigned_team == filters["assigned_team"])
            if filters.get("assigned_to"):
                query = query.filter(Complaint.assigned_to == filters["assigned_to"])
            if filters.get("needs_human_review") is not None:
                needs_review = filters["needs_human_review"]
                if isinstance(needs_review, str):
                    needs_review = needs_review.lower() == "true"
                query = query.filter(Complaint.needs_human_review == needs_review)
            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    db.or_(
                        Complaint.reference.ilike(search_term),
                        Complaint.description.ilike(search_term),
                        Complaint.customer_name.ilike(search_term),
                    )
                )

        # Sort by priority (critical first) then by creation date (oldest first)
        priority_order = db.case(
            (Complaint.current_priority == "critical", 0),
            (Complaint.current_priority == "high", 1),
            (Complaint.current_priority == "medium", 2),
            (Complaint.current_priority == "low", 3),
            else_=4
        )

        query = query.order_by(priority_order, Complaint.created_at.asc())

        complaints = query.all()
        return [c.to_support_dict() for c in complaints]

    @staticmethod
    def update_complaint(complaint_id: str, data: dict, user_id: str,
                         user_name: str, user_role: str) -> dict:
        """Update complaint fields with audit logging."""
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return None

        changes = []

        # Status change
        if "status" in data:
            new_status = data["status"]
            old_status = complaint.status

            # Validate status transition
            valid_transitions = ComplaintService.STATUS_TRANSITIONS.get(old_status, [])
            if new_status not in valid_transitions:
                return {"error": f"Cannot transition from {old_status} to {new_status}"}

            complaint.status = new_status
            if new_status == "resolved":
                from backend.models import utcnow
                complaint.resolved_at = utcnow()
            elif new_status == "closed":
                from backend.models import utcnow
                complaint.closed_at = utcnow()

            # Record status change
            status_record = StatusHistory(
                complaint_id=complaint.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=user_id,
                changed_by_name=user_name,
                reason=data.get("reason", ""),
            )
            db.session.add(status_record)

            # Customer notification
            status_label = ComplaintService.STATUS_LABELS.get(new_status, new_status)
            notification = Notification(
                complaint_id=complaint.id,
                customer_id=complaint.customer_id,
                message=f"Your complaint status has been updated to: {status_label}",
                notification_type="status_update",
            )
            db.session.add(notification)

            changes.append(("status", old_status, new_status))

        # Manual category override
        if "manual_category" in data:
            if user_role not in ("admin", "manager", "agent"):
                return {"error": "Insufficient permissions to change category"}
            old_cat = complaint.manual_category or complaint.system_category
            complaint.manual_category = data["manual_category"]
            complaint.current_category = data["manual_category"]
            if "manual_subcategory" in data:
                complaint.manual_subcategory = data["manual_subcategory"]
                complaint.current_subcategory = data["manual_subcategory"]
            changes.append(("category", old_cat, data["manual_category"]))

        # Manual priority override
        if "manual_priority" in data:
            if user_role not in ("admin", "manager"):
                return {"error": "Insufficient permissions to change priority"}
            old_pri = complaint.manual_priority or complaint.system_priority
            complaint.manual_priority = data["manual_priority"]
            complaint.current_priority = data["manual_priority"]
            changes.append(("priority", old_pri, data["manual_priority"]))

        # Needs human review flag
        if "needs_human_review" in data:
            complaint.needs_human_review = data["needs_human_review"]

        # Record audit logs
        for field, old_val, new_val in changes:
            audit = AuditLog(
                entity_type="complaint",
                entity_id=complaint.id,
                action=f"{field}_changed",
                old_value=str(old_val),
                new_value=str(new_val),
                user_id=user_id,
                user_name=user_name,
            )
            db.session.add(audit)

        db.session.commit()
        return complaint.to_support_dict()

    @staticmethod
    def assign_complaint(complaint_id: str, assigned_to: str = None,
                         team: str = None, assigner_id: str = None,
                         assigner_name: str = None) -> dict:
        """Assign or reassign a complaint."""
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return None

        if assigned_to:
            complaint.assigned_to = assigned_to
        if team:
            complaint.assigned_team = team

        # If complaint is still in submitted status, move to under_review
        if complaint.status == "submitted":
            old_status = complaint.status
            complaint.status = "under_review"
            status_record = StatusHistory(
                complaint_id=complaint.id,
                old_status=old_status,
                new_status="under_review",
                changed_by=assigner_id or "system",
                changed_by_name=assigner_name or "System",
                reason="Complaint assigned to agent",
            )
            db.session.add(status_record)

        # Record assignment
        assignment = Assignment(
            complaint_id=complaint.id,
            assigned_to=assigned_to,
            assigned_by=assigner_id,
            team=team or complaint.assigned_team,
        )
        db.session.add(assignment)

        # Audit
        audit = AuditLog(
            entity_type="complaint",
            entity_id=complaint.id,
            action="assigned",
            new_value=json.dumps({
                "assigned_to": assigned_to,
                "team": team or complaint.assigned_team,
            }),
            user_id=assigner_id,
            user_name=assigner_name,
        )
        db.session.add(audit)

        db.session.commit()
        return complaint.to_support_dict()

    @staticmethod
    def add_internal_note(complaint_id: str, content: str,
                          author_id: str) -> dict:
        """Add an internal note to a complaint."""
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return None

        note = InternalNote(
            complaint_id=complaint.id,
            author_id=author_id,
            content=sanitize_text(content),
        )
        db.session.add(note)

        audit = AuditLog(
            entity_type="complaint",
            entity_id=complaint.id,
            action="note_added",
            user_id=author_id,
        )
        db.session.add(audit)

        db.session.commit()
        return note.to_dict()

    @staticmethod
    def resolve_complaint(complaint_id: str, user_id: str,
                          user_name: str, resolution_note: str = None) -> dict:
        """Resolve a complaint."""
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return None

        old_status = complaint.status
        complaint.status = "resolved"
        from backend.models import utcnow
        complaint.resolved_at = utcnow()

        status_record = StatusHistory(
            complaint_id=complaint.id,
            old_status=old_status,
            new_status="resolved",
            changed_by=user_id,
            changed_by_name=user_name,
            reason=resolution_note or "Complaint resolved",
        )
        db.session.add(status_record)

        if resolution_note:
            note = InternalNote(
                complaint_id=complaint.id,
                author_id=user_id,
                content=f"Resolution: {sanitize_text(resolution_note)}",
            )
            db.session.add(note)

        notification = Notification(
            complaint_id=complaint.id,
            customer_id=complaint.customer_id,
            message="Your complaint has been resolved. If you have further questions, please contact us.",
            notification_type="resolution",
        )
        db.session.add(notification)

        db.session.commit()
        return complaint.to_support_dict()

    @staticmethod
    def reopen_complaint(complaint_id: str, user_id: str,
                         user_name: str, reason: str = None) -> dict:
        """Reopen a resolved or closed complaint."""
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return None

        if complaint.status not in ("resolved", "closed"):
            return {"error": "Only resolved or closed complaints can be reopened"}

        old_status = complaint.status
        complaint.status = "in_progress"
        complaint.resolved_at = None
        complaint.closed_at = None

        status_record = StatusHistory(
            complaint_id=complaint.id,
            old_status=old_status,
            new_status="in_progress",
            changed_by=user_id,
            changed_by_name=user_name,
            reason=reason or "Complaint reopened",
        )
        db.session.add(status_record)

        notification = Notification(
            complaint_id=complaint.id,
            customer_id=complaint.customer_id,
            message="Your complaint has been reopened and is being reviewed again.",
            notification_type="status_update",
        )
        db.session.add(notification)

        db.session.commit()
        return complaint.to_support_dict()

    @staticmethod
    def get_analytics_overview() -> dict:
        """Get analytics overview for the support dashboard."""
        from sqlalchemy import func

        total = Complaint.query.count()
        open_statuses = ["submitted", "under_review", "in_progress", "waiting_for_customer"]

        total_open = Complaint.query.filter(Complaint.status.in_(open_statuses)).count()
        total_resolved = Complaint.query.filter_by(status="resolved").count()
        total_closed = Complaint.query.filter_by(status="closed").count()

        # By priority
        critical = Complaint.query.filter(
            Complaint.current_priority == "critical",
            Complaint.status.in_(open_statuses)
        ).count()
        high = Complaint.query.filter(
            Complaint.current_priority == "high",
            Complaint.status.in_(open_statuses)
        ).count()
        medium = Complaint.query.filter(
            Complaint.current_priority == "medium",
            Complaint.status.in_(open_statuses)
        ).count()
        low = Complaint.query.filter(
            Complaint.current_priority == "low",
            Complaint.status.in_(open_statuses)
        ).count()

        # Needs human review
        needs_review = Complaint.query.filter(
            Complaint.needs_human_review == True,
            Complaint.status.in_(open_statuses)
        ).count()

        # Unassigned
        unassigned = Complaint.query.filter(
            Complaint.assigned_to == None,
            Complaint.status.in_(open_statuses)
        ).count()

        # By category
        by_category = db.session.query(
            Complaint.current_category, func.count(Complaint.id)
        ).filter(
            Complaint.status.in_(open_statuses)
        ).group_by(Complaint.current_category).all()

        # By status
        by_status = db.session.query(
            Complaint.status, func.count(Complaint.id)
        ).group_by(Complaint.status).all()

        # Recent complaints (last 10)
        recent = Complaint.query.order_by(
            Complaint.created_at.desc()
        ).limit(10).all()

        # Recently resolved
        recently_resolved = Complaint.query.filter_by(
            status="resolved"
        ).order_by(Complaint.resolved_at.desc()).limit(10).all()

        return {
            "total": total,
            "total_open": total_open,
            "total_resolved": total_resolved,
            "total_closed": total_closed,
            "by_priority": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
            },
            "needs_review": needs_review,
            "unassigned": unassigned,
            "by_category": [
                {"category": cat or "Uncategorized", "count": count}
                for cat, count in by_category
            ],
            "by_status": [
                {"status": status, "count": count}
                for status, count in by_status
            ],
            "recent_complaints": [c.to_support_dict() for c in recent],
            "recently_resolved": [c.to_support_dict() for c in recently_resolved],
        }
