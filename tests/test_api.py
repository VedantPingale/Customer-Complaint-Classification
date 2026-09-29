"""API endpoint tests.

Tests for:
- Complaint creation and reference generation
- Customer data isolation
- Authentication and authorization
- Support role permissions
- Status transitions
- Manual overrides
- Audit logging
"""

import pytest
from tests.conftest import auth_header


class TestCustomerAPI:
    """Tests for customer-facing API endpoints."""

    def test_submit_complaint_success(self, client):
        """Test successful complaint submission."""
        resp = client.post("/api/customer/complaints", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "description": "I noticed an unauthorized charge of $200 on my credit card statement.",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "reference" in data
        assert data["reference"].startswith("CMP-")
        assert data["status"] == "submitted"
        assert data["message"] == "Complaint submitted successfully."

    def test_submit_complaint_missing_fields(self, client):
        """Test complaint submission with missing required fields."""
        resp = client.post("/api/customer/complaints", json={
            "name": "Jane",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "errors" in data

    def test_submit_complaint_short_description(self, client):
        """Test complaint submission with too-short description."""
        resp = client.post("/api/customer/complaints", json={
            "name": "Jane",
            "email": "jane@example.com",
            "description": "short",
        })
        assert resp.status_code == 400

    def test_submit_complaint_invalid_email(self, client):
        """Test complaint submission with invalid email."""
        resp = client.post("/api/customer/complaints", json={
            "name": "Jane",
            "email": "not-an-email",
            "description": "This is a detailed complaint about a billing issue on my account.",
        })
        assert resp.status_code == 400

    def test_submit_complaint_no_body(self, client):
        """Test complaint submission with no request body."""
        resp = client.post("/api/customer/complaints",
                          content_type="application/json")
        assert resp.status_code == 400

    def test_track_complaint_success(self, client, sample_complaint):
        """Test tracking a complaint by reference number."""
        resp = client.get(f"/api/customer/complaints/{sample_complaint}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["reference"] == sample_complaint
        assert "status" in data
        assert "timeline" in data
        # Verify no internal data is exposed
        assert "system_confidence" not in data
        assert "priority_explanation" not in data
        assert "internal_notes" not in data
        assert "system_priority" not in data
        assert "assigned_to" not in data

    def test_track_complaint_not_found(self, client):
        """Test tracking a non-existent complaint."""
        resp = client.get("/api/customer/complaints/CMP-0000-00000")
        assert resp.status_code == 404

    def test_reference_uniqueness(self, client):
        """Test that each complaint gets a unique reference."""
        refs = set()
        for i in range(5):
            resp = client.post("/api/customer/complaints", json={
                "name": f"Customer {i}",
                "email": f"customer{i}@test.com",
                "description": f"This is complaint number {i} with sufficient detail for testing.",
            })
            assert resp.status_code == 201
            ref = resp.get_json()["reference"]
            assert ref not in refs
            refs.add(ref)

    def test_customer_data_isolation(self, client, sample_complaint):
        """Test that customer API never exposes internal data."""
        resp = client.get(f"/api/customer/complaints/{sample_complaint}")
        data = resp.get_json()

        internal_fields = [
            "system_confidence", "system_category", "system_subcategory",
            "system_priority", "priority_explanation", "priority_signals",
            "model_version", "needs_human_review", "assigned_team",
            "assigned_to", "internal_notes", "manual_category",
            "manual_priority", "manual_subcategory", "current_category",
            "current_priority", "current_subcategory", "id",
        ]

        for field in internal_fields:
            assert field not in data, f"Internal field '{field}' exposed to customer"


class TestSupportAuthentication:
    """Tests for support authentication."""

    def test_login_success(self, client, support_users):
        """Test successful support login."""
        resp = client.post("/api/support/login", json={
            "username": "testadmin",
            "password": "testpass123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"

    def test_login_invalid_password(self, client, support_users):
        """Test login with wrong password."""
        resp = client.post("/api/support/login", json={
            "username": "testadmin",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, support_users):
        """Test login with non-existent username."""
        resp = client.post("/api/support/login", json={
            "username": "nobody",
            "password": "testpass123",
        })
        assert resp.status_code == 401

    def test_protected_endpoint_without_token(self, client, db):
        """Test accessing a protected endpoint without authentication."""
        resp = client.get("/api/support/complaints")
        assert resp.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client, db):
        """Test accessing a protected endpoint with an invalid token."""
        resp = client.get("/api/support/complaints",
                         headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_get_current_user(self, client, admin_token):
        """Test getting the current user profile."""
        resp = client.get("/api/support/me", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["username"] == "testadmin"


class TestSupportAuthorization:
    """Tests for role-based access control."""

    def test_agent_cannot_assign_complaint(self, client, agent_token, sample_complaint, db):
        """Test that agents cannot assign complaints."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        resp = client.post(
            f"/api/support/complaints/{complaint.id}/assign",
            json={"assigned_to": "some-id"},
            headers=auth_header(agent_token),
        )
        assert resp.status_code == 403

    def test_agent_cannot_reopen_complaint(self, client, agent_token, sample_complaint, db):
        """Test that agents cannot reopen complaints."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        resp = client.post(
            f"/api/support/complaints/{complaint.id}/reopen",
            json={},
            headers=auth_header(agent_token),
        )
        assert resp.status_code == 403

    def test_admin_can_create_user(self, client, admin_token):
        """Test that admins can create new support users."""
        resp = client.post("/api/support/users",
            json={
                "username": "newagent",
                "email": "newagent@test.com",
                "password": "newpass123",
                "role": "agent",
                "display_name": "New Agent",
            },
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 201
        assert resp.get_json()["user"]["username"] == "newagent"

    def test_agent_cannot_create_user(self, client, agent_token):
        """Test that agents cannot create users."""
        resp = client.post("/api/support/users",
            json={
                "username": "another",
                "email": "another@test.com",
                "password": "pass123",
                "role": "agent",
                "display_name": "Another",
            },
            headers=auth_header(agent_token),
        )
        assert resp.status_code == 403


class TestSupportComplaintManagement:
    """Tests for support complaint management."""

    def test_list_complaints(self, client, admin_token, sample_complaint):
        """Test listing complaints as support staff."""
        resp = client.get("/api/support/complaints",
                         headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert "complaints" in data
        assert len(data["complaints"]) >= 1

    def test_get_complaint_detail(self, client, admin_token, sample_complaint, db):
        """Test getting full complaint details as support staff."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        resp = client.get(f"/api/support/complaints/{complaint.id}",
                         headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()

        # Support should see internal data
        assert "system_confidence" in data
        assert "system_category" in data
        assert "system_priority" in data
        assert "priority_explanation" in data
        assert "needs_human_review" in data

    def test_update_status(self, client, admin_token, sample_complaint, db):
        """Test updating complaint status."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        resp = client.patch(
            f"/api/support/complaints/{complaint.id}",
            json={"status": "under_review"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "under_review"

    def test_invalid_status_transition(self, client, admin_token, sample_complaint, db):
        """Test that invalid status transitions are rejected."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        # submitted -> resolved directly should fail
        resp = client.patch(
            f"/api/support/complaints/{complaint.id}",
            json={"status": "resolved"},
            headers=auth_header(admin_token),
        )
        # submitted doesn't transition directly to resolved in our rules
        # Actually let's check - the STATUS_TRANSITIONS for submitted includes:
        # ["under_review", "in_progress", "closed"]
        # So "resolved" should fail
        assert resp.status_code == 400

    def test_add_internal_note(self, client, admin_token, sample_complaint, db):
        """Test adding an internal note."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        resp = client.post(
            f"/api/support/complaints/{complaint.id}/notes",
            json={"content": "Initial review notes."},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 201
        assert resp.get_json()["content"] == "Initial review notes."

    def test_manual_priority_override(self, client, admin_token, sample_complaint, db):
        """Test manual priority override."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        resp = client.patch(
            f"/api/support/complaints/{complaint.id}",
            json={"manual_priority": "critical"},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["manual_priority"] == "critical"
        assert data["current_priority"] == "critical"
        # System priority should be preserved
        assert data["system_priority"] is not None

    def test_assign_complaint(self, client, manager_token, support_users, sample_complaint, db):
        """Test assigning a complaint to an agent."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()
        agent = support_users["agent"]

        resp = client.post(
            f"/api/support/complaints/{complaint.id}/assign",
            json={"assigned_to": agent.id},
            headers=auth_header(manager_token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["assigned_to"] == agent.id

    def test_resolve_complaint(self, client, admin_token, sample_complaint, db):
        """Test resolving a complaint."""
        from backend.models import Complaint
        complaint = Complaint.query.filter_by(reference=sample_complaint).first()

        # First move to a resolvable status
        client.patch(
            f"/api/support/complaints/{complaint.id}",
            json={"status": "in_progress"},
            headers=auth_header(admin_token),
        )

        resp = client.post(
            f"/api/support/complaints/{complaint.id}/resolve",
            json={"resolution_note": "Issue has been resolved."},
            headers=auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "resolved"

    def test_filter_complaints_by_priority(self, client, admin_token, sample_complaint):
        """Test filtering complaints by priority."""
        resp = client.get("/api/support/complaints?priority=high",
                         headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_filter_complaints_by_status(self, client, admin_token, sample_complaint):
        """Test filtering complaints by status."""
        resp = client.get("/api/support/complaints?status=submitted",
                         headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_search_complaints(self, client, admin_token, sample_complaint):
        """Test searching complaints."""
        resp = client.get(f"/api/support/complaints?search={sample_complaint}",
                         headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["complaints"]) >= 1


class TestAnalytics:
    """Tests for analytics endpoints."""

    def test_analytics_overview(self, client, admin_token, sample_complaint):
        """Test analytics overview endpoint."""
        resp = client.get("/api/support/analytics/overview",
                         headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert "total" in data
        assert "total_open" in data
        assert "by_priority" in data
        assert "by_category" in data

    def test_analytics_requires_auth(self, client, db):
        """Test that analytics requires authentication."""
        resp = client.get("/api/support/analytics/overview")
        assert resp.status_code == 401
