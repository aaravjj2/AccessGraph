"""Regenerates the shared artefacts that other modules consume.

    shared/schemas/clinical_evidence.schema.json
    shared/schemas/clinical_extract_request.schema.json
    services/clinical_agent/examples/acl_case_output.json
    shared/sample_data/*.json

Run with ``python scripts/generate_schema.py`` after changing the contract or
the sample case.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVICE_ROOT.parent.parent
sys.path.insert(0, str(SERVICE_ROOT))

from app.contracts import ClinicalEvidence, ExtractRequest  # noqa: E402
from app.extract import extract_clinical_evidence  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    evidence_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://accessgraph.dev/schemas/clinical_evidence.schema.json",
        "description": (
            "Structured, source-backed clinical evidence produced by the "
            "AccessGraph Clinical Evidence Agent."
        ),
        **ClinicalEvidence.model_json_schema(),
    }
    request_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://accessgraph.dev/schemas/clinical_extract_request.schema.json",
        "description": "Request body for POST /clinical/extract.",
        **ExtractRequest.model_json_schema(),
    }

    write_json(REPO_ROOT / "shared/schemas/clinical_evidence.schema.json", evidence_schema)
    write_json(REPO_ROOT / "shared/schemas/clinical_extract_request.schema.json", request_schema)

    sample_path = SERVICE_ROOT / "examples/acl_case_input.json"
    sample_input = json.loads(sample_path.read_text(encoding="utf-8"))
    evidence = extract_clinical_evidence(ExtractRequest.model_validate(sample_input)).evidence

    write_json(SERVICE_ROOT / "examples/acl_case_output.json", evidence.model_dump())
    write_json(REPO_ROOT / "shared/sample_data/acl_case_clinical_evidence.json", evidence.model_dump())
    write_json(REPO_ROOT / "shared/sample_data/acl_case_clinical_input.json", sample_input)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
