"""Shared types and helpers for the individual fact extractors."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from ..contracts import ClinicalDocument, SourceRef
from ..text.dates import find_date
from ..text.segment import Segment, segment_document

T = TypeVar("T")

_IMAGING_LABEL = re.compile(
    r"\b(?:mri|magnetic resonance|imaging|radiolog(?:y|ic)|arthrogram)\b", re.IGNORECASE
)
_IMAGING_TITLE = re.compile(r"\b(?:mri|magnetic resonance|mr imaging)\b", re.IGNORECASE)
_LINE_BREAK = re.compile(r"\r?\n")


@dataclass(frozen=True)
class PreparedDoc:
    """A document plus everything the extractors need precomputed."""

    source_id: str
    source_label: str
    #: Explicit provenance override supplied by the caller, if any.
    location_override: str | None
    #: Document date from the request, or the first date found in the text.
    date: str | None
    #: True when the document as a whole is an imaging study report.
    is_imaging: bool
    segments: list[Segment]


@dataclass(frozen=True)
class TraceEntry:
    """One line of "why did the agent decide this".

    Returned by the debug endpoint and shown in the QC UI. Never part of the
    ClinicalEvidence contract.
    """

    field: str
    decision: str
    source_id: str | None = None
    page: int | None = None
    matched_text: str | None = None
    #: True when this entry explains evidence that was accepted.
    accepted: bool = False


@dataclass
class Finding(Generic[T]):
    value: T
    citations: list[SourceRef] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


def _detect_imaging(doc: ClinicalDocument) -> bool:
    """Only the label and title line decide imaging context.

    Keying off body text would misclassify a clinic note that merely mentions
    an MRI in its plan.
    """
    if _IMAGING_LABEL.search(doc.source_label):
        return True
    title_line = next((line for line in _LINE_BREAK.split(doc.text) if line.strip()), "")
    return bool(_IMAGING_TITLE.search(title_line))


def prepare_document(doc: ClinicalDocument) -> PreparedDoc:
    return PreparedDoc(
        source_id=doc.source_id,
        source_label=doc.source_label,
        location_override=doc.location,
        date=doc.document_date or find_date(doc.text),
        is_imaging=_detect_imaging(doc),
        segments=segment_document(doc.text),
    )


def location_for(doc: PreparedDoc, segment: Segment) -> str:
    return doc.location_override or f"page {segment.page}"


def cite(doc: PreparedDoc, segment: Segment, fact: str) -> SourceRef:
    return SourceRef(
        fact=fact,
        source_id=doc.source_id,
        source_label=doc.source_label,
        location=location_for(doc, segment),
    )
