"""Every failure leaves this service in one predictable shape.

.. code-block:: json

    {"error": {"code": "...", "message": "...", "details": [...]}}
"""

from __future__ import annotations

from typing import Any


class ClinicalAgentError(Exception):
    """Base class for every error this service returns to a caller."""

    def __init__(
        self,
        code: str,
        status: int,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message
        self.details = details or []

    def to_body(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class InvalidRequestError(ClinicalAgentError):
    def __init__(self, message: str, details: list[dict[str, str]] | None = None) -> None:
        super().__init__("INVALID_REQUEST", 400, message, details)


class UnsupportedProcedureError(ClinicalAgentError):
    def __init__(self, procedure: str, supported: list[str]) -> None:
        super().__init__(
            "UNSUPPORTED_PROCEDURE",
            422,
            f'No extraction rule pack for procedure "{procedure}".',
            [{"path": "procedure", "message": f"supported procedures: {', '.join(supported)}"}],
        )


class SchemaViolationError(ClinicalAgentError):
    def __init__(self, issues: list[dict[str, Any]]) -> None:
        super().__init__(
            "SCHEMA_VIOLATION",
            500,
            "Extraction produced output that does not satisfy the ClinicalEvidence contract.",
            [
                {
                    "path": ".".join(str(part) for part in issue.get("loc", ())),
                    "message": str(issue.get("msg", "")),
                }
                for issue in issues
            ],
        )


def error_body(code: str, message: str, details: list[dict[str, str]] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or []}}
