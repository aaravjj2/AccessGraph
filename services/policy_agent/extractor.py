"""Deterministic, source-backed extraction for procedure-specific payer policies."""

import re
from typing import Any

from schema import validate_policy_requirements


class PolicyExtractionError(ValueError):
    pass


def _location(text: str, pattern: str) -> str:
    """Return a stable human-readable location from a labelled section or line."""
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return "Policy text"
    start = text.rfind("\n", 0, match.start()) + 1
    line = text[start:text.find("\n", start) if text.find("\n", start) != -1 else len(text)].strip()
    section = re.search(r"(?:section|criteria)\s+([\d.]+)", line, re.IGNORECASE)
    return f"Section {section.group(1)}" if section else "Policy text"


def _requirement(
    criterion_id: str, description: str, kind: str, required_value: Any,
    source_label: str, source_location: str, unit: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "criterion_id": criterion_id,
        "description": description,
        "type": kind,
        "required_value": required_value,
        "source_label": source_label,
        "source_location": source_location,
    }
    if unit is not None:
        item["unit"] = unit
    return item


def _extract_acl_requirements(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for document in documents:
        text = document["text"]
        label = document["source_label"]
        if re.search(r"\bmri\b.*(?:confirm|evidence)|(?:confirm|evidence).*\bmri\b", text, re.I):
            found.setdefault("MRI_CONFIRMED", _requirement(
                "MRI_CONFIRMED", "MRI confirmation of ACL tear", "boolean", True, label,
                _location(text, r"\bmri\b"),
            ))
        pt_match = re.search(r"(?:at least|minimum of|no fewer than)\s+(\d+)\s+weeks?[^.\n]*(?:physical therapy|conservative treatment)|(?:physical therapy|conservative treatment)[^.\n]*(?:at least|minimum of|no fewer than)\s+(\d+)\s+weeks?", text, re.I)
        if pt_match:
            weeks = int(next(value for value in pt_match.groups() if value is not None))
            found.setdefault("PT_WEEKS", _requirement(
                "PT_WEEKS", f"At least {weeks} weeks of physical therapy", "numeric_min", weeks,
                label, _location(text, r"(?:physical therapy|conservative treatment)"), "weeks",
            ))
        if re.search(r"persistent\s+(?:functional\s+)?(?:knee\s+)?instability", text, re.I):
            found.setdefault("PERSISTENT_INSTABILITY", _requirement(
                "PERSISTENT_INSTABILITY", "Persistent functional instability", "boolean", True,
                label, _location(text, r"persistent\s+(?:functional\s+)?(?:knee\s+)?instability"),
            ))
        if re.search(r"recent\s+(?:qualifying\s+)?physical\s+exam(?:ination)?", text, re.I):
            found.setdefault("RECENT_PHYSICAL_EXAM", _requirement(
                "RECENT_PHYSICAL_EXAM", "Recent qualifying physical examination", "boolean", True,
                label, _location(text, r"recent\s+(?:qualifying\s+)?physical\s+exam"),
            ))
    return [found[key] for key in ("MRI_CONFIRMED", "PT_WEEKS", "PERSISTENT_INSTABILITY", "RECENT_PHYSICAL_EXAM") if key in found]


def extract_policy_requirements(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract requirements only stated in supplied policy documents.

    This service deliberately has no patient fields, readiness calculations, or costs.
    """
    required = ("insurer", "procedure", "documents")
    if not isinstance(payload, dict) or any(not payload.get(key) for key in required):
        raise PolicyExtractionError("insurer, procedure, and a non-empty documents list are required")
    documents = payload["documents"]
    if not isinstance(documents, list) or not documents:
        raise PolicyExtractionError("documents must be a non-empty list")
    for doc in documents:
        if not isinstance(doc, dict) or not all(isinstance(doc.get(key), str) and doc[key].strip() for key in ("source_id", "source_label", "text")):
            raise PolicyExtractionError("each document requires non-empty source_id, source_label, and text")

    procedure = payload["procedure"]
    requirements = _extract_acl_requirements(documents) if procedure == "ACL_RECONSTRUCTION" else []
    result = {
        "insurer": payload["insurer"],
        "procedure": procedure,
        "policy_version": payload.get("policy_version") or None,
        "requirements": requirements,
    }
    validate_policy_requirements(result)
    return result
