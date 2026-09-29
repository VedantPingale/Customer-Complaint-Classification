"""Input sanitization and validation utilities."""

import re
import html


def sanitize_text(text: str) -> str:
    """Sanitize user input text by escaping HTML and trimming whitespace."""
    if not text:
        return ""
    text = text.strip()
    text = html.escape(text)
    return text


def sanitize_email(email: str) -> str:
    """Sanitize and validate email format."""
    if not email:
        return ""
    email = email.strip().lower()
    return email


def validate_email(email: str) -> bool:
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def mask_email(email: str) -> str:
    """Mask an email address for display purposes.

    Example: john.doe@example.com -> j****e@example.com
    """
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


def mask_sensitive_data(text: str) -> str:
    """Mask potential sensitive data like card numbers, SSNs, and account numbers.

    This is a best-effort approach and should not be relied upon as the sole
    protection mechanism.
    """
    if not text:
        return text

    # Mask potential card numbers (13-19 digits)
    text = re.sub(
        r'\b(\d{4})\s*[\-\s]?\d{4}\s*[\-\s]?\d{4}\s*[\-\s]?(\d{1,7})\b',
        r'\1-XXXX-XXXX-\2',
        text
    )

    # Mask potential SSN patterns
    text = re.sub(
        r'\b(\d{3})[\-\s]?(\d{2})[\-\s]?\d{4}\b',
        r'\1-\2-XXXX',
        text
    )

    # Mask potential account numbers (8+ consecutive digits)
    text = re.sub(
        r'\b(\d{2})\d{6,}(\d{2})\b',
        r'\1XXXXXX\2',
        text
    )

    return text


def validate_complaint_input(data: dict) -> list:
    """Validate complaint submission data. Returns a list of error messages."""
    errors = []

    if not data.get("name") or not data["name"].strip():
        errors.append("Name is required.")

    if not data.get("email") or not data["email"].strip():
        errors.append("Email is required.")
    elif not validate_email(data["email"]):
        errors.append("Please provide a valid email address.")

    if not data.get("description") or not data["description"].strip():
        errors.append("Complaint description is required.")
    elif len(data["description"].strip()) < 20:
        errors.append("Please provide a more detailed description (at least 20 characters).")
    elif len(data["description"].strip()) > 10000:
        errors.append("Complaint description must be less than 10,000 characters.")

    name = data.get("name", "")
    if len(name) > 200:
        errors.append("Name must be less than 200 characters.")

    return errors
