from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

SERVICE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_ROOT))

from app.contracts import ClinicalEvidence, ExtractRequest  # noqa: E402
from app.extract import extract_clinical_evidence  # noqa: E402


def read_json(relative: str) -> Any:
    return json.loads((SERVICE_ROOT / relative).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sample_input() -> dict[str, Any]:
    return read_json("examples/acl_case_input.json")


@pytest.fixture(scope="session")
def sample_output() -> dict[str, Any]:
    return read_json("examples/acl_case_output.json")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def extract_from_text(
    text: str,
    *,
    source_id: str = "doc_01",
    source_label: str = "Clinical Note",
    document_date: str | None = None,
    location: str | None = None,
    **overrides: Any,
) -> ClinicalEvidence:
    """Runs extraction over one inline document."""
    document: dict[str, Any] = {
        "source_id": source_id,
        "source_label": source_label,
        "text": text,
    }
    if document_date:
        document["document_date"] = document_date
    if location:
        document["location"] = location

    request = ExtractRequest.model_validate(
        {
            "patient_id": "P001",
            "procedure": "ACL_RECONSTRUCTION",
            "documents": [document],
            **overrides,
        }
    )
    return extract_clinical_evidence(request).evidence
