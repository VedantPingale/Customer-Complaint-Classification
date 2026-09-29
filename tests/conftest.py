"""Pytest configuration and shared fixtures."""

import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.models import db as _db
from backend.auth import hash_password


@pytest.fixture(scope="session")
def app():
    """Create the Flask application for testing."""
    app = create_app(TestingConfig)
    return app


@pytest.fixture(scope="function")
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def support_users(db):
    """Create test support users."""
    from backend.models import SupportUser

    admin = SupportUser(
        username="testadmin",
        email="admin@test.com",
        password_hash=hash_password("testpass123"),
        role="admin",
        display_name="Test Admin",
    )
    manager = SupportUser(
        username="testmanager",
        email="manager@test.com",
        password_hash=hash_password("testpass123"),
        role="manager",
        display_name="Test Manager",
    )
    agent = SupportUser(
        username="testagent",
        email="agent@test.com",
        password_hash=hash_password("testpass123"),
        role="agent",
        display_name="Test Agent",
    )

    db.session.add_all([admin, manager, agent])
    db.session.commit()

    return {"admin": admin, "manager": manager, "agent": agent}


@pytest.fixture
def admin_token(client, support_users):
    """Get a JWT token for the admin user."""
    resp = client.post("/api/support/login", json={
        "username": "testadmin",
        "password": "testpass123",
    })
    return resp.get_json()["token"]


@pytest.fixture
def manager_token(client, support_users):
    """Get a JWT token for the manager user."""
    resp = client.post("/api/support/login", json={
        "username": "testmanager",
        "password": "testpass123",
    })
    return resp.get_json()["token"]


@pytest.fixture
def agent_token(client, support_users):
    """Get a JWT token for the agent user."""
    resp = client.post("/api/support/login", json={
        "username": "testagent",
        "password": "testpass123",
    })
    return resp.get_json()["token"]


@pytest.fixture
def sample_complaint(client):
    """Create a sample complaint and return the reference."""
    resp = client.post("/api/customer/complaints", json={
        "name": "Test Customer",
        "email": "customer@test.com",
        "description": "I was charged an unauthorized fee of $500 on my credit card "
                       "and I need this resolved immediately. The transaction was fraudulent.",
    })
    data = resp.get_json()
    return data["reference"]


def auth_header(token):
    """Create an authorization header dict."""
    return {"Authorization": f"Bearer {token}"}
