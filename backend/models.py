"""SQLAlchemy database models for the complaint management system."""

import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def generate_uuid():
    """Generate a UUID string for use as a primary key."""
    return str(uuid.uuid4())


def utcnow():
    """Return the current UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


class Customer(db.Model):
    """Customer who submits complaints."""

    __tablename__ = "customers"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    complaints = db.relationship("Complaint", backref="customer", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SupportUser(db.Model):
    """Internal support staff user."""

    __tablename__ = "support_users"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="agent")  # admin, manager, agent
    display_name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Complaint(db.Model):
    """Core complaint record."""

    __tablename__ = "complaints"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.String(36), db.ForeignKey("customers.id"), nullable=False)

    # Customer-provided information
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    product_type = db.Column(db.String(200), nullable=True)

    # System-generated classification
    system_category = db.Column(db.String(200), nullable=True)
    system_subcategory = db.Column(db.String(200), nullable=True)
    system_confidence = db.Column(db.Float, nullable=True)
    model_version = db.Column(db.String(100), nullable=True)

    # Manual classification overrides
    manual_category = db.Column(db.String(200), nullable=True)
    manual_subcategory = db.Column(db.String(200), nullable=True)

    # System-generated priority
    system_priority = db.Column(db.String(20), nullable=True)
    priority_explanation = db.Column(db.Text, nullable=True)
    priority_signals = db.Column(db.Text, nullable=True)  # JSON string of signals

    # Manual priority override
    manual_priority = db.Column(db.String(20), nullable=True)

    # Current effective values (computed from system + manual)
    current_category = db.Column(db.String(200), nullable=True)
    current_subcategory = db.Column(db.String(200), nullable=True)
    current_priority = db.Column(db.String(20), nullable=True, default="medium")

    # Status
    status = db.Column(db.String(50), nullable=False, default="submitted")
    needs_human_review = db.Column(db.Boolean, default=False)

    # Assignment
    assigned_team = db.Column(db.String(100), nullable=True)
    assigned_to = db.Column(db.String(36), db.ForeignKey("support_users.id"), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    assignee = db.relationship("SupportUser", foreign_keys=[assigned_to])
    classifications = db.relationship("Classification", backref="complaint", lazy="dynamic",
                                       order_by="Classification.created_at.desc()")
    priority_decisions = db.relationship("PriorityDecision", backref="complaint", lazy="dynamic",
                                          order_by="PriorityDecision.created_at.desc()")
    status_history = db.relationship("StatusHistory", backref="complaint", lazy="dynamic",
                                      order_by="StatusHistory.created_at.desc()")
    internal_notes = db.relationship("InternalNote", backref="complaint", lazy="dynamic",
                                      order_by="InternalNote.created_at.desc()")
    assignments = db.relationship("Assignment", backref="complaint", lazy="dynamic",
                                   order_by="Assignment.assigned_at.desc()")
    notifications = db.relationship("Notification", backref="complaint", lazy="dynamic",
                                     order_by="Notification.created_at.desc()")

    def to_customer_dict(self):
        """Return customer-safe data only."""
        return {
            "reference": self.reference,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def to_support_dict(self):
        """Return full internal data for support staff."""
        return {
            "id": self.id,
            "reference": self.reference,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "description": self.description,
            "product_type": self.product_type,
            "system_category": self.system_category,
            "system_subcategory": self.system_subcategory,
            "system_confidence": self.system_confidence,
            "model_version": self.model_version,
            "manual_category": self.manual_category,
            "manual_subcategory": self.manual_subcategory,
            "current_category": self.current_category,
            "current_subcategory": self.current_subcategory,
            "system_priority": self.system_priority,
            "manual_priority": self.manual_priority,
            "current_priority": self.current_priority,
            "priority_explanation": self.priority_explanation,
            "status": self.status,
            "needs_human_review": self.needs_human_review,
            "assigned_team": self.assigned_team,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.display_name if self.assignee else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }

    # Priority ordering for sorting
    PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    VALID_STATUSES = [
        "submitted", "under_review", "in_progress",
        "waiting_for_customer", "resolved", "closed"
    ]


class Classification(db.Model):
    """Record of each classification run on a complaint."""

    __tablename__ = "classifications"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    category = db.Column(db.String(200), nullable=False)
    subcategory = db.Column(db.String(200), nullable=True)
    confidence = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "subcategory": self.subcategory,
            "confidence": self.confidence,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PriorityDecision(db.Model):
    """Record of each priority calculation for a complaint."""

    __tablename__ = "priority_decisions"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Float, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    signals = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "priority": self.priority,
            "score": self.score,
            "explanation": self.explanation,
            "signals": self.signals,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StatusHistory(db.Model):
    """Audit trail for status changes."""

    __tablename__ = "status_history"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    changed_by = db.Column(db.String(36), nullable=True)  # support user ID or 'system'
    changed_by_name = db.Column(db.String(200), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "changed_by_name": self.changed_by_name,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Assignment(db.Model):
    """Record of complaint assignments."""

    __tablename__ = "assignments"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    assigned_to = db.Column(db.String(36), db.ForeignKey("support_users.id"), nullable=True)
    assigned_by = db.Column(db.String(36), db.ForeignKey("support_users.id"), nullable=True)
    team = db.Column(db.String(100), nullable=True)
    assigned_at = db.Column(db.DateTime, default=utcnow)

    assignee = db.relationship("SupportUser", foreign_keys=[assigned_to])
    assigner = db.relationship("SupportUser", foreign_keys=[assigned_by])

    def to_dict(self):
        return {
            "id": self.id,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.display_name if self.assignee else None,
            "assigned_by": self.assigned_by,
            "assigner_name": self.assigner.display_name if self.assigner else None,
            "team": self.team,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
        }


class InternalNote(db.Model):
    """Internal notes visible only to support staff."""

    __tablename__ = "internal_notes"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    author_id = db.Column(db.String(36), db.ForeignKey("support_users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    author = db.relationship("SupportUser", foreign_keys=[author_id])

    def to_dict(self):
        return {
            "id": self.id,
            "author_id": self.author_id,
            "author_name": self.author.display_name if self.author else None,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    """General audit log for tracking all changes."""

    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    entity_type = db.Column(db.String(50), nullable=False)  # complaint, user, etc.
    entity_id = db.Column(db.String(36), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String(36), nullable=True)
    user_name = db.Column(db.String(200), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    """Customer-facing notifications about complaint updates."""

    __tablename__ = "notifications"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey("customers.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), default="status_update")  # status_update, info, resolution
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "message": self.message,
            "is_read": self.is_read,
            "notification_type": self.notification_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
