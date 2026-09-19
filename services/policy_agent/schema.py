"""Validation for the shared PolicyRequirements API contract."""

from typing import Any


VALID_TYPES = {"boolean", "numeric_min", "numeric_max", "categorical", "text_presence"}


def validate_policy_requirements(value: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ValueError("PolicyRequirements must be an object")
    for key in ("insurer", "procedure", "requirements"):
        if key not in value:
            raise ValueError(f"PolicyRequirements missing {key}")
    if not isinstance(value["insurer"], str) or not isinstance(value["procedure"], str):
        raise ValueError("insurer and procedure must be strings")
    if value.get("policy_version") is not None and not isinstance(value["policy_version"], str):
        raise ValueError("policy_version must be a string or null")
    if not isinstance(value["requirements"], list):
        raise ValueError("requirements must be an array")
    ids: set[str] = set()
    for requirement in value["requirements"]:
        required = ("criterion_id", "description", "type", "required_value", "source_label", "source_location")
        if not isinstance(requirement, dict) or any(key not in requirement for key in required):
            raise ValueError("each requirement must contain all canonical fields")
        if requirement["criterion_id"] in ids:
            raise ValueError("criterion_id values must be unique")
        ids.add(requirement["criterion_id"])
        if requirement["type"] not in VALID_TYPES:
            raise ValueError(f"unsupported requirement type: {requirement['type']}")
        if any(not isinstance(requirement[key], str) or not requirement[key] for key in ("criterion_id", "description", "source_label", "source_location")):
            raise ValueError("criterion and source fields must be non-empty strings")
        if requirement["type"] in {"numeric_min", "numeric_max"} and not isinstance(requirement["required_value"], (int, float)):
            raise ValueError("numeric criteria require a numeric required_value")
