"""FastAPI surface for the Clinical Evidence Agent."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from .contracts import SUPPORTED_PROCEDURES, ClinicalEvidence, ExtractRequest
from .errors import ClinicalAgentError, error_body
from .extract import extract_clinical_evidence

SERVICE_NAME = "clinical_agent"
SERVICE_VERSION = "1.0.0"

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_UI_INDEX = Path(__file__).resolve().parent / "ui" / "index.html"
_SAMPLE_CASE = _SERVICE_ROOT / "examples" / "acl_case_input.json"

app = FastAPI(
    title="AccessGraph Clinical Evidence Agent",
    version=SERVICE_VERSION,
    description=(
        "Converts synthetic patient medical records into structured, "
        "source-backed ClinicalEvidence JSON."
    ),
)


# ---------------------------------------------------------------------------
# Error handling: one predictable envelope for every failure
# ---------------------------------------------------------------------------


@app.exception_handler(ClinicalAgentError)
async def handle_agent_error(_request: Request, error: ClinicalAgentError) -> JSONResponse:
    return JSONResponse(status_code=error.status, content=error.to_body())


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    details = [
        {
            # Drop the leading "body" element so paths read like the contract.
            "path": ".".join(str(part) for part in issue["loc"][1:]) or "(root)",
            "message": issue["msg"],
        }
        for issue in error.errors()
    ]
    message = (
        "Request body is not valid JSON."
        if any(issue["type"] == "json_invalid" for issue in error.errors())
        else "Request body does not match the clinical extract contract."
    )
    return JSONResponse(
        status_code=400, content=error_body("INVALID_REQUEST", message, details)
    )


@app.exception_handler(404)
async def handle_not_found(request: Request, _exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("NOT_FOUND", f"No route for {request.method} {request.url.path}."),
    )


@app.exception_handler(Exception)
async def handle_unexpected(_request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500, content=error_body("INTERNAL_ERROR", str(error) or "Unexpected error.")
    )


# ---------------------------------------------------------------------------
# Contract routes
# ---------------------------------------------------------------------------


@app.post("/clinical/extract", response_model=ClinicalEvidence, tags=["contract"])
async def extract(request: ExtractRequest) -> ClinicalEvidence:
    """The contract. Returns exactly ClinicalEvidence."""
    return extract_clinical_evidence(request).evidence


@app.post("/clinical/extract/debug", tags=["debug"])
async def extract_debug(request: ExtractRequest) -> dict[str, Any]:
    """Same extraction plus the decision trace. Not part of the contract."""
    result = extract_clinical_evidence(request)
    return {
        "evidence": result.evidence.model_dump(),
        "as_of_date": result.as_of_date,
        "trace": [asdict(entry) for entry in result.trace],
    }


@app.get("/clinical/schema", tags=["contract"])
async def clinical_schema() -> dict[str, Any]:
    """JSON Schema for ClinicalEvidence, so other modules can validate."""
    return ClinicalEvidence.model_json_schema()


@app.get("/health", tags=["ops"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "supported_procedures": list(SUPPORTED_PROCEDURES),
    }


# ---------------------------------------------------------------------------
# Quality-check UI
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def ui_index() -> FileResponse:
    return FileResponse(_UI_INDEX, media_type="text/html")


@app.get("/ui/sample-case", tags=["ui"])
async def sample_case() -> dict[str, Any]:
    """The shared synthetic ACL case, so the UI can load it in one click."""
    return json.loads(_SAMPLE_CASE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    # Port 8000 is the Orchestrator and 8001 is the Policy Agent.
    import os

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8002")))
