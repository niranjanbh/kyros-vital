"""PHI redaction in structlog — verifies PHI keys never reach the log output."""
from typing import Any

import pytest

from app.core.logging import redact_phi


def test_phi_keys_are_redacted() -> None:
    event_dict: dict[str, Any] = {
        "event": "admin.audit",
        "notes": "patient has type 2 diabetes",
        "payload": {"sensitive_field": "value123"},
        "dose": "500mg twice daily",
        "lab_value": "HbA1c 7.4%",
        "result": "positive",
        "metadata": {"drug": "metformin"},
        "keep_this": "safe field",
        "action": "admin.read.consultation_detail",
    }

    result = redact_phi(None, "info", event_dict)

    assert result["notes"] == "[REDACTED]"
    assert result["payload"] == "[REDACTED]"
    assert result["dose"] == "[REDACTED]"
    assert result["lab_value"] == "[REDACTED]"
    assert result["result"] == "[REDACTED]"
    assert result["metadata"] == "[REDACTED]"

    # Non-PHI fields must pass through unchanged
    assert result["keep_this"] == "safe field"
    assert result["action"] == "admin.read.consultation_detail"
    assert result["event"] == "admin.audit"


def test_phi_redaction_on_empty_dict() -> None:
    result = redact_phi(None, "info", {})
    assert result == {}


def test_phi_redaction_leaves_unknown_keys_intact() -> None:
    event_dict: dict[str, Any] = {"user_id": "abc123", "status": "ok"}
    result = redact_phi(None, "info", event_dict)
    assert result == {"user_id": "abc123", "status": "ok"}


def test_phi_redaction_is_idempotent() -> None:
    event_dict: dict[str, Any] = {"notes": "sensitive", "event": "test"}
    result1 = redact_phi(None, "info", event_dict)
    result2 = redact_phi(None, "info", result1)
    assert result2["notes"] == "[REDACTED]"
