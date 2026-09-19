"""The extraction pipeline: prepare, extract, validate, return."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from .contracts import (
    DEFAULT_RECENCY_WINDOW_DAYS,
    SUPPORTED_PROCEDURES,
    ClinicalEvidence,
    ExtractRequest,
    SourceRef,
)
from .errors import SchemaViolationError, UnsupportedProcedureError
from .extractors.base import Finding, TraceEntry, prepare_document
from .extractors.diagnosis import extract_diagnosis
from .extractors.instability import extract_persistent_instability
from .extractors.mri import extract_mri_confirmed
from .extractors.nsaid import extract_nsaid_trial
from .extractors.physical_exam import extract_recent_physical_exam
from .extractors.physical_therapy import extract_physical_therapy_weeks
from .text.dates import latest_date


@dataclass(frozen=True)
class ExtractionResult:
    evidence: ClinicalEvidence
    trace: list[TraceEntry]
    #: Reference date used for recency checks, echoed for debugging.
    as_of_date: str | None


def _dedupe(sources: list[SourceRef]) -> list[SourceRef]:
    seen: set[tuple[str, ...]] = set()
    unique: list[SourceRef] = []
    for source in sources:
        key = (source.fact, source.source_id, source.source_label, source.location)
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def extract_clinical_evidence(request: ExtractRequest) -> ExtractionResult:
    """Runs the deterministic ACL rule pack over the supplied records.

    Deterministic in the strict sense: the same request always produces the
    same bytes. Nothing here consults the wall clock, a model, or the network.
    """
    if request.procedure not in SUPPORTED_PROCEDURES:
        raise UnsupportedProcedureError(request.procedure, list(SUPPORTED_PROCEDURES))

    docs = [prepare_document(doc) for doc in request.documents]
    as_of_date = request.as_of_date or latest_date(doc.date for doc in docs)
    recency_window_days = request.recency_window_days or DEFAULT_RECENCY_WINDOW_DAYS

    diagnosis = extract_diagnosis(docs)
    mri = extract_mri_confirmed(docs)
    pt_weeks = extract_physical_therapy_weeks(docs)
    nsaid = extract_nsaid_trial(docs)
    instability = extract_persistent_instability(docs)
    exam = extract_recent_physical_exam(docs, as_of_date, recency_window_days)

    # Fixed order keeps `sources` byte-stable across runs.
    ordered: list[Finding] = [diagnosis, mri, pt_weeks, nsaid, instability, exam]

    try:
        evidence = ClinicalEvidence(
            patient_id=request.patient_id,
            procedure=request.procedure,
            diagnosis=diagnosis.value,
            evidence={
                "mri_confirmed": mri.value,
                "physical_therapy_weeks": pt_weeks.value,
                "persistent_instability": instability.value,
                "nsaid_trial": nsaid.value,
                "recent_physical_exam": exam.value,
            },
            sources=_dedupe([c for finding in ordered for c in finding.citations]),
        )
    except ValidationError as error:
        # A failure here is an internal bug, not bad input: fail loudly rather
        # than emit something the Orchestrator cannot consume.
        raise SchemaViolationError(error.errors()) from error

    return ExtractionResult(
        evidence=evidence,
        trace=[entry for finding in ordered for entry in finding.trace],
        as_of_date=as_of_date,
    )
