"""Canonical AccessGraph contracts owned by the Clinical Evidence Agent.

Field names here are shared across all four modules. Renaming anything in
``ClinicalEvidence`` requires team approval (see docs/api_contract.md).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

#: Supported procedures. Each needs its own extraction rule pack.
SUPPORTED_PROCEDURES: tuple[str, ...] = ("ACL_RECONSTRUCTION",)

DEFAULT_RECENCY_WINDOW_DAYS = 90

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
IsoDate = Annotated[str, StringConstraints(pattern=ISO_DATE_PATTERN)]


# ---------------------------------------------------------------------------
# Output contract: ClinicalEvidence
# ---------------------------------------------------------------------------


class SourceRef(BaseModel):
    """One citation supporting one extracted fact."""

    model_config = ConfigDict(extra="forbid")

    fact: NonEmptyStr
    source_id: NonEmptyStr
    source_label: NonEmptyStr
    location: NonEmptyStr


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mri_confirmed: bool
    physical_therapy_weeks: int = Field(ge=0)
    persistent_instability: bool
    nsaid_trial: bool
    recent_physical_exam: bool


class ClinicalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: NonEmptyStr
    procedure: NonEmptyStr
    #: Required but nullable. The key is always present so downstream consumers
    #: never have to distinguish "absent" from "no diagnosis documented".
    diagnosis: NonEmptyStr | None
    evidence: Evidence
    sources: list[SourceRef]


# ---------------------------------------------------------------------------
# Input contract: POST /clinical/extract
# ---------------------------------------------------------------------------


class ClinicalDocument(BaseModel):
    """Input is lenient: unknown keys are ignored, not rejected."""

    model_config = ConfigDict(extra="ignore")

    source_id: NonEmptyStr
    source_label: NonEmptyStr
    text: str
    #: Date the document was authored, used for physical-exam recency.
    document_date: IsoDate | None = None
    #: Overrides the derived ``page N`` provenance string for this document.
    location: NonEmptyStr | None = None


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    patient_id: NonEmptyStr
    procedure: NonEmptyStr
    documents: list[ClinicalDocument] = Field(min_length=1)
    #: Reference date for recency checks. Omit and the agent uses the newest
    #: date found in the documents, which keeps extraction reproducible.
    as_of_date: IsoDate | None = None
    #: How recent a physical exam must be to count. Defaults to 90 days.
    recency_window_days: int | None = Field(default=None, gt=0, le=3650)
