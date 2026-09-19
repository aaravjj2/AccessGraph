"""Deterministic AccessGraph case orchestrator for the synthetic ACL demo.

This is a synthetic, in-memory demo workflow. It evaluates policy requirements
deterministically and never submits to a payer or handles real patient data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AccessGraph Orchestrator", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

CASE_ID = "P001"
PROCEDURE = "ACL_RECONSTRUCTION"
INSURER = "ExampleHealth PPO"
PT_REQUIRED_DAYS = 42
INITIAL_PT_DAYS = 35
EXTERNAL_PT_DAYS = 14


class AnalyzeRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=80)
    procedure: str = Field(min_length=1, max_length=80)
    insurer: str = Field(min_length=1, max_length=160)


class CaseAssistantRequest(AnalyzeRequest):
    question: str = Field(min_length=1, max_length=1200)


class CaseAssistantResponse(BaseModel):
    answer: str
    citations: list[str]
    suggested_questions: list[str]
    disclaimer: str


class MissingRequirement(BaseModel):
    criterion_id: str
    description: str
    recommended_action: str


class Explanation(BaseModel):
    criterion_id: str
    patient_evidence: str
    payer_requirement: str
    result: Literal["SATISFIED", "UNSATISFIED", "UNKNOWN", "CONFLICTING"]


class CostEstimate(BaseModel):
    low: int = Field(ge=0)
    high: int = Field(ge=0)
    currency: Literal["USD"]
    basis: str


class IdentityStatus(BaseModel):
    provider_agent_verified: bool
    insurer_agent_verified: bool


class AuthorizationResult(BaseModel):
    patient_id: str
    procedure: str
    status: Literal["BLOCKED", "READY_FOR_REVIEW"]
    authorization_readiness: float = Field(ge=0, le=1)
    requirements_met: int = Field(ge=0)
    requirements_total: int = Field(ge=0)
    missing_requirements: list[MissingRequirement]
    estimated_patient_cost: CostEstimate
    identity_status: IdentityStatus
    explanations: list[Explanation]


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


def _error(code: str, message: str) -> dict:
    return {"code": code, "message": message}


@app.exception_handler(HTTPException)
async def handle_http_error(_request: Request, error: HTTPException) -> JSONResponse:
    if isinstance(error.detail, dict) and "code" in error.detail:
        return JSONResponse(status_code=error.status_code, content=error.detail)
    code = "CASE_NOT_FOUND" if error.status_code == 404 else "INVALID_REQUEST"
    return JSONResponse(status_code=error.status_code, content=_error(code, str(error.detail)))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, _error_value: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=_error("INVALID_REQUEST", "Request does not match the case analysis contract."),
    )


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


def _citations(*explanations: Explanation) -> list[str]:
    """Return only references already contained in the evaluated case."""
    citations: list[str] = []
    for explanation in explanations:
        for text in (explanation.patient_evidence, explanation.payer_requirement):
            if "[Source: " not in text:
                continue
            citation = text.split("[Source: ", maxsplit=1)[1].rstrip("]")
            if citation not in citations:
                citations.append(citation)
    return citations


def _assistant_reply(question: str, result: AuthorizationResult) -> CaseAssistantResponse:
    """Provide bounded, deterministic case guidance for the HCP side agent."""
    normalized = " ".join(question.lower().split())
    by_id = {item.criterion_id: item for item in result.explanations}
    missing_ids = [item.criterion_id for item in result.missing_requirements]
    missing_explanations = [by_id[item_id] for item_id in missing_ids if item_id in by_id]
    suggestions = [
        "What is blocking this case?",
        "What does the cost estimate mean?",
        "Which sources support the findings?",
    ]
    disclaimer = "Case guidance is based on the available synthetic evidence and policy criteria. It does not determine coverage or insurer authorization."

    if any(term in normalized for term in ("cost", "price", "out of pocket", "deductible", "pay")):
        cost = result.estimated_patient_cost
        return CaseAssistantResponse(
            answer=f"The current synthetic estimate is ${cost.low:,}–${cost.high:,} {cost.currency}. It is based on {cost.basis.lower()}; actual patient responsibility can change with benefits, billing, and coverage.",
            citations=[],
            suggested_questions=["What is blocking this case?", "Which sources support the findings?", "What should the care team do next?"],
            disclaimer=disclaimer,
        )

    if any(term in normalized for term in ("agent", "identity", "verify", "trusted")):
        provider = "verified" if result.identity_status.provider_agent_verified else "not yet verified"
        insurer = "verified" if result.identity_status.insurer_agent_verified else "not yet verified"
        return CaseAssistantResponse(
            answer=f"The synthetic provider/PT agent is {provider}; the synthetic insurer agent is {insurer}. Verification controls whether external PT evidence can enter this demo case.",
            citations=[],
            suggested_questions=["What is blocking this case?", "What should the care team do next?", "What does the cost estimate mean?"],
            disclaimer=disclaimer,
        )

    if any(term in normalized for term in ("source", "document", "policy", "evidence", "support")):
        citations = _citations(*result.explanations)
        return CaseAssistantResponse(
            answer="The findings are backed by the source references listed below. Open a criterion in the case review to compare the patient evidence with the payer requirement.",
            citations=citations,
            suggested_questions=["What is blocking this case?", "Why is PT duration flagged?", "What should the care team do next?"],
            disclaimer=disclaimer,
        )

    if any(term in normalized for term in ("pt", "therapy", "conservative", "duration")):
        pt = by_id["PT_DURATION"]
        return CaseAssistantResponse(
            answer=f"{pt.patient_evidence.split(' [Source:')[0]} {pt.payer_requirement.split(' [Source:')[0]} In this demo, verified PT evidence can add the remaining documented days after the PT agent is verified.",
            citations=_citations(pt),
            suggested_questions=["How do I verify the PT agent?", "What is blocking this case?", "Which sources support the findings?"],
            disclaimer=disclaimer,
        )

    if any(term in normalized for term in ("instability", "lachman", "exam", "physical")):
        instability = by_id["FUNCTIONAL_INSTABILITY"]
        return CaseAssistantResponse(
            answer=f"{instability.patient_evidence.split(' [Source:')[0]} The next step is to confirm that finding through the human-review control in this synthetic workflow.",
            citations=_citations(instability),
            suggested_questions=["What is blocking this case?", "Why is PT duration flagged?", "Which sources support the findings?"],
            disclaimer=disclaimer,
        )

    if result.status == "READY_FOR_REVIEW":
        return CaseAssistantResponse(
            answer=f"All {result.requirements_total} synthetic criteria are currently satisfied. The case is ready for human review, not guaranteed insurer approval. Review the source rationale with the care team before submitting.",
            citations=_citations(*result.explanations),
            suggested_questions=["Which sources support the findings?", "What does the cost estimate mean?", "What should the care team do next?"],
            disclaimer=disclaimer,
        )

    actions = "; ".join(item.recommended_action for item in result.missing_requirements)
    return CaseAssistantResponse(
        answer=f"The case is currently {result.status.lower().replace('_', ' ')}: {result.requirements_met} of {result.requirements_total} criteria are satisfied. The next actions are: {actions}.",
        citations=_citations(*missing_explanations),
        suggested_questions=suggestions,
        disclaimer=disclaimer,
    )


def evaluate() -> AuthorizationResult:
    """Evaluate all seven synthetic requirements without side effects."""
    pt_days = INITIAL_PT_DAYS + (EXTERNAL_PT_DAYS if state.external_pt_received else 0)
    instability_result = "SATISFIED" if state.instability_confirmed else "UNKNOWN"
    pt_result = "SATISFIED" if pt_days >= PT_REQUIRED_DAYS else "UNSATISFIED"
    explanations = [
        Explanation(criterion_id="MRI_CONFIRMED", patient_evidence=_source("MRI confirms complete ACL tear.", "MRI Report, page 1"), payer_requirement=_source("MRI confirmation of ACL tear.", "ACL Policy 2026.09, Section 3.1"), result="SATISFIED"),
        Explanation(criterion_id="PERSISTENT_SYMPTOMS", patient_evidence=_source("Persistent giving-way symptoms documented.", "PT Progress Note, page 2"), payer_requirement=_source("Persistent symptoms must be documented.", "ACL Policy 2026.09, Section 4.1"), result="SATISFIED"),
        Explanation(criterion_id="FAILED_CONSERVATIVE_TREATMENT", patient_evidence=_source("NSAID trial and supervised PT documented.", "Medication History, page 1"), payer_requirement=_source("Failed conservative treatment is required.", "ACL Policy 2026.09, Section 4.2"), result="SATISFIED"),
        Explanation(criterion_id="RECENT_PHYSICAL_EXAM", patient_evidence=_source("Orthopedic exam is dated within the 90-day policy window.", "Orthopedic Note, page 1"), payer_requirement=_source("Recent qualifying physical examination.", "ACL Policy 2026.09, Section 4.4"), result="SATISFIED"),
        Explanation(criterion_id="DIAGNOSIS_CODING", patient_evidence=_source("ACL tear diagnosis is present in the synthetic case.", "Orthopedic Note, Assessment"), payer_requirement=_source("Relevant diagnosis coding is required.", "ACL Policy 2026.09, Section 5.1"), result="SATISFIED"),
        Explanation(criterion_id="PT_DURATION", patient_evidence=_source(f"{pt_days} documented days of conservative therapy; {PT_REQUIRED_DAYS} required.", "PT Encounter Timeline, synthetic"), payer_requirement=_source(f"At least {PT_REQUIRED_DAYS} days of conservative therapy.", "ACL Policy 2026.09, Section 4.3"), result=pt_result),
        Explanation(criterion_id="FUNCTIONAL_INSTABILITY", patient_evidence=_source("Clinician confirmed positive Lachman finding as functional instability." if state.instability_confirmed else "Positive Lachman test found; clinician confirmation required.", "Orthopedic Note, page 1"), payer_requirement=_source("Functional instability must be documented.", "ACL Policy 2026.09, Section 3.2"), result=instability_result),
    ]
    met = sum(item.result == "SATISFIED" for item in explanations)
    missing: list[MissingRequirement] = []
    if not state.instability_confirmed:
        missing.append(MissingRequirement(criterion_id="FUNCTIONAL_INSTABILITY", description="Potential instability evidence requires clinician confirmation", recommended_action="Confirm the positive Lachman finding"))
    if pt_days < PT_REQUIRED_DAYS:
        missing.append(MissingRequirement(criterion_id="PT_DURATION", description=f"Conservative therapy is {PT_REQUIRED_DAYS - pt_days} documented days short", recommended_action="Verify the PT agent and add the missing PT documentation"))
    return AuthorizationResult(
        patient_id=CASE_ID, procedure=PROCEDURE,
        status="READY_FOR_REVIEW" if met == 7 else "BLOCKED",
        authorization_readiness=round(met / len(explanations), 4),
        requirements_met=met, requirements_total=len(explanations),
        missing_requirements=missing,
        estimated_patient_cost=CostEstimate(low=1450, high=1900, currency="USD", basis="Synthetic deductible and coinsurance estimate"),
        identity_status=IdentityStatus(provider_agent_verified=state.pt_agent_verified, insurer_agent_verified=True),
        explanations=explanations,
    )


def _require_case(case_id: str) -> None:
    if case_id != CASE_ID:
        raise HTTPException(status_code=404, detail=_error("CASE_NOT_FOUND", "Synthetic case not found."))


def _validate(request: AnalyzeRequest) -> None:
    if request.patient_id != CASE_ID or request.procedure != PROCEDURE:
        raise HTTPException(status_code=422, detail=_error("NO_CLINICAL_EVIDENCE", "No registered synthetic case matches the request."))
    if request.insurer != INSURER:
        raise HTTPException(status_code=422, detail=_error("NO_POLICY", "No matching synthetic payer policy is available."))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "orchestrator", "version": "1.1.0", "synthetic_data_only": True}


@app.post("/analyze-case", response_model=AuthorizationResult)
def analyze_case(request: AnalyzeRequest) -> AuthorizationResult:
    _validate(request)
    return evaluate()


@app.post("/case-assistant", response_model=CaseAssistantResponse)
def case_assistant(request: CaseAssistantRequest) -> CaseAssistantResponse:
    """Bounded side-agent endpoint. It never changes case state."""
    _validate(request)
    return _assistant_reply(request.question, evaluate())


@app.post("/cases/{case_id}/confirm-instability", response_model=AuthorizationResult)
def confirm_instability(case_id: str) -> AuthorizationResult:
    _require_case(case_id)
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
    return {"agent_id": "pt-agent", "verified": True, "synthetic": True}


@app.post("/cases/{case_id}/external-pt-evidence", response_model=AuthorizationResult)
def external_pt_evidence(case_id: str) -> AuthorizationResult:
    _require_case(case_id)
    if not state.pt_agent_verified:
        raise HTTPException(status_code=403, detail=_error("UNVERIFIED_AGENT", "PT evidence is quarantined until agent verification."))
    if not state.external_pt_received:
        state.external_pt_received = True
        _record("EVIDENCE_FOUND", "Verified PT agent supplied 14 additional documented therapy days.")
        _record("REQUIREMENT_SATISFIED", "Conservative therapy duration is now 49 of 42 days.")
        _record("CASE_READY", "All policy requirements are satisfied; human review remains required.")
    return evaluate()


@app.get("/cases/{case_id}/audit", response_model=list[AuditEvent])
def audit(case_id: str) -> list[AuditEvent]:
    _require_case(case_id)
    return state.audit.copy()


@app.post("/cases/{case_id}/reset", response_model=AuthorizationResult)
def reset(case_id: str) -> AuthorizationResult:
    _require_case(case_id)
    reset_state()
    return evaluate()
