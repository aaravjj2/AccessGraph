"""Deterministic AccessGraph case orchestrator for the synthetic ACL demo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="AccessGraph Orchestrator", version="1.0.0")

CASE_ID = "P001"
PROCEDURE = "ACL_RECONSTRUCTION"
INSURER = "ExampleHealth PPO"
PT_REQUIRED_DAYS = 42
INITIAL_PT_DAYS = 35
EXTERNAL_PT_DAYS = 14


class AnalyzeRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    procedure: str = Field(min_length=1)
    insurer: str = Field(min_length=1)


class AuditEvent(BaseModel):
    event: str
    detail: str
    at: str


class CaseState(BaseModel):
    instability_confirmed: bool = False
    pt_agent_verified: bool = False
    external_pt_received: bool = False
    audit: list[AuditEvent] = Field(default_factory=list)


state = CaseState()


def _record(event: str, detail: str) -> None:
    state.audit.append(
        AuditEvent(event=event, detail=detail, at=datetime.now(timezone.utc).isoformat())
    )


def reset_state() -> None:
    global state
    state = CaseState()
    _record("CASE_CREATED", "Synthetic ACL authorization case created.")
    _record("POLICY_LOADED", "ExampleHealth ACL policy version 2026.09 selected.")


reset_state()


def _source(text: str, source: str) -> str:
    return f"{text} [Source: {source}]"


def evaluate() -> dict:
    pt_days = INITIAL_PT_DAYS + (EXTERNAL_PT_DAYS if state.external_pt_received else 0)
    instability_result = "SATISFIED" if state.instability_confirmed else "UNKNOWN"
    pt_result = "SATISFIED" if pt_days >= PT_REQUIRED_DAYS else "UNSATISFIED"

    explanations = [
        {
            "criterion_id": "MRI_CONFIRMED",
            "patient_evidence": _source("MRI confirms complete ACL tear.", "MRI Report, page 1"),
            "payer_requirement": _source("MRI confirmation of ACL tear.", "ACL Policy 2026.09, Section 3.1"),
            "result": "SATISFIED",
        },
        {
            "criterion_id": "PERSISTENT_SYMPTOMS",
            "patient_evidence": _source("Persistent giving-way symptoms documented.", "PT Progress Note, page 2"),
            "payer_requirement": _source("Persistent symptoms must be documented.", "ACL Policy 2026.09, Section 4.1"),
            "result": "SATISFIED",
        },
        {
            "criterion_id": "FAILED_CONSERVATIVE_TREATMENT",
            "patient_evidence": _source("NSAID trial and supervised PT documented.", "Medication History, page 1"),
            "payer_requirement": _source("Failed conservative treatment is required.", "ACL Policy 2026.09, Section 4.2"),
            "result": "SATISFIED",
        },
        {
            "criterion_id": "RECENT_PHYSICAL_EXAM",
            "patient_evidence": _source("Orthopedic exam is dated within the 90-day policy window.", "Orthopedic Note, page 1"),
            "payer_requirement": _source("Recent qualifying physical examination.", "ACL Policy 2026.09, Section 4.4"),
            "result": "SATISFIED",
        },
        {
            "criterion_id": "DIAGNOSIS_CODING",
            "patient_evidence": _source("ACL tear diagnosis is present in the synthetic case.", "Orthopedic Note, Assessment"),
            "payer_requirement": _source("Relevant diagnosis coding is required.", "ACL Policy 2026.09, Section 5.1"),
            "result": "SATISFIED",
        },
        {
            "criterion_id": "PT_DURATION",
            "patient_evidence": _source(
                f"{pt_days} documented days of conservative therapy; {PT_REQUIRED_DAYS} required.",
                "PT Encounter Timeline, synthetic",
            ),
            "payer_requirement": _source(
                f"At least {PT_REQUIRED_DAYS} days of conservative therapy.",
                "ACL Policy 2026.09, Section 4.3",
            ),
            "result": pt_result,
        },
        {
            "criterion_id": "FUNCTIONAL_INSTABILITY",
            "patient_evidence": _source(
                "Positive Lachman test found; clinician confirmation required."
                if not state.instability_confirmed
                else "Clinician confirmed positive Lachman finding as functional instability.",
                "Orthopedic Note, page 1",
            ),
            "payer_requirement": _source(
                "Functional instability must be documented.", "ACL Policy 2026.09, Section 3.2"
            ),
            "result": instability_result,
        },
    ]
    met = sum(item["result"] == "SATISFIED" for item in explanations)
    missing = []
    if not state.instability_confirmed:
        missing.append({
            "criterion_id": "FUNCTIONAL_INSTABILITY",
            "description": "Potential instability evidence requires clinician confirmation",
            "recommended_action": "Confirm the positive Lachman finding",
        })
    if pt_days < PT_REQUIRED_DAYS:
        missing.append({
            "criterion_id": "PT_DURATION",
            "description": f"Conservative therapy is {PT_REQUIRED_DAYS - pt_days} documented days short",
            "recommended_action": "Verify the PT agent and add the missing PT documentation",
        })
    return {
        "patient_id": CASE_ID,
        "procedure": PROCEDURE,
        "status": "READY_FOR_REVIEW" if met == 7 else "BLOCKED",
        "authorization_readiness": round(met / 7, 4),
        "requirements_met": met,
        "requirements_total": 7,
        "missing_requirements": missing,
        "estimated_patient_cost": {
            "low": 1450,
            "high": 1900,
            "currency": "USD",
            "basis": "Synthetic deductible and coinsurance estimate",
        },
        "identity_status": {
            "provider_agent_verified": state.pt_agent_verified,
            "insurer_agent_verified": True,
        },
        "explanations": explanations,
    }


def _validate(request: AnalyzeRequest) -> None:
    if request.patient_id != CASE_ID or request.procedure != PROCEDURE:
        raise HTTPException(status_code=422, detail={"code": "NO_CLINICAL_EVIDENCE"})
    if request.insurer != INSURER:
        raise HTTPException(status_code=422, detail={"code": "NO_POLICY"})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "orchestrator", "synthetic_data_only": True}


@app.post("/analyze-case")
def analyze_case(request: AnalyzeRequest) -> dict:
    _validate(request)
    return evaluate()


@app.post("/cases/{case_id}/confirm-instability")
def confirm_instability(case_id: str) -> dict:
    if case_id != CASE_ID:
        raise HTTPException(status_code=404, detail="case not found")
    if not state.instability_confirmed:
        state.instability_confirmed = True
        _record("HUMAN_EVIDENCE_CONFIRMATION", "Clinician confirmed positive Lachman finding.")
        _record("REQUIREMENT_SATISFIED", "Functional instability requirement satisfied.")
    return evaluate()


@app.post("/agents/pt-agent/verify")
def verify_pt_agent() -> dict:
    if not state.pt_agent_verified:
        state.pt_agent_verified = True
        _record("AGENT_IDENTITY_VERIFIED", "Synthetic PT agent verified through simulated ANS.")
    return {"agent_id": "pt-agent", "verified": True}


@app.post("/cases/{case_id}/external-pt-evidence")
def external_pt_evidence(case_id: str) -> dict:
    if case_id != CASE_ID:
        raise HTTPException(status_code=404, detail="case not found")
    if not state.pt_agent_verified:
        raise HTTPException(
            status_code=403,
            detail={"code": "UNVERIFIED_AGENT", "message": "PT evidence is quarantined until agent verification."},
        )
    if not state.external_pt_received:
        state.external_pt_received = True
        _record("EVIDENCE_FOUND", "Verified PT agent supplied 14 additional documented therapy days.")
        _record("REQUIREMENT_SATISFIED", "Conservative therapy duration is now 49 of 42 days.")
        _record("CASE_READY", "All policy requirements are satisfied; human review remains required.")
    return evaluate()


@app.get("/cases/{case_id}/audit")
def audit(case_id: str) -> list[dict]:
    if case_id != CASE_ID:
        raise HTTPException(status_code=404, detail="case not found")
    return [event.model_dump() for event in state.audit]


@app.post("/cases/{case_id}/reset")
def reset(case_id: str) -> dict:
    if case_id != CASE_ID:
        raise HTTPException(status_code=404, detail="case not found")
    reset_state()
    return evaluate()
