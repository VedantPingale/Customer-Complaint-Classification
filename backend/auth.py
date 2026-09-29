"""Authentication and authorization utilities."""

import datetime
import functools
import jwt
import bcrypt
from flask import request, jsonify, current_app, g
from backend.models import db, SupportUser


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id: str, username: str, role: str) -> str:
    """Create a JWT token for an authenticated support user."""
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        hours=current_app.config.get("JWT_EXPIRATION_HOURS", 8)
    )
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expiration,
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    """Extract the current user from the JWT token in the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return None

    user = SupportUser.query.get(payload["user_id"])
    if not user or not user.is_active:
        return None

    return user


def login_required(f):
    """Decorator to require authentication for a route."""

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        g.current_user = user
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    """Decorator to require specific roles for a route."""

    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if user.role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            g.current_user = user
            return f(*args, **kwargs)

        return decorated

    return decorator


def admin_required(f):
    """Decorator to require admin role."""
    return role_required("admin")(f)


def manager_or_admin_required(f):
    """Decorator to require manager or admin role."""
    return role_required("admin", "manager")(f)
