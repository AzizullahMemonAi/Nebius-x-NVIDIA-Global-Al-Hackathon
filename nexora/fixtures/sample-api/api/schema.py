"""Request schema validation for the sample API demo workspace.

Contains a known bug: ``validate_payload`` raises the wrong error type, which
breaks the documented backward-compatible error contract.
"""
from typing import Any, Dict

MAX_NAME_LENGTH = 120


class ValidationError(Exception):
    """Client-correctable input error. Carries a stable ``code``."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_name(value: Any) -> str:
    if value is None:
        raise ValidationError("name_required", "name is required")
    if not isinstance(value, str):
        # BUG: callers expect ValidationError but receive a bare TypeError,
        # which the error handler maps to a 500 instead of a 400.
        raise TypeError("name must be a string")
    value = value.strip()
    if not value:
        raise ValidationError("name_required", "name is required")
    if len(value) > MAX_NAME_LENGTH:
        raise ValidationError("name_too_long", f"name exceeds {MAX_NAME_LENGTH} characters")
    return value


def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("payload_not_object", "payload must be an object")

    cleaned = {
        "name": validate_name(payload.get("name")),
        "count": int(payload.get("count", 1)),
    }
    if cleaned["count"] < 0:
        raise ValidationError("count_invalid", "count must be >= 0")
    return cleaned
