from __future__ import annotations

import re
from dataclasses import dataclass

from ..text.dates import days_between
from ..text.negation import is_negated
from ..text.segment import Segment
from .base import Finding, PreparedDoc, TraceEntry, cite

FIELD = "evidence.recent_physical_exam"

#: An explicit exam section header is on its own strong evidence of an exam.
EXAM_SECTION = re.compile(
    r"\b(?:physical exam(?:ination)?|musculoskeletal exam(?:ination)?"
    r"|knee exam(?:ination)?|objective findings|on examination|exam)\s*:",
    re.IGNORECASE,
)

#: Individual manoeuvres and findings; two or more imply a real exam.
EXAM_FINDING = re.compile(
    r"\b(?:lachman|pivot[- ]shift|anterior drawer|posterior drawer|mcmurray"
    r"|valgus stress|varus stress|range of motion|ROM|effusion"
    r"|joint line tenderness|crepitus|antalgic|gait"
    r"|quadriceps (?:strength|atrophy)|ligamentous exam)\b",
    re.IGNORECASE,
)

MIN_FINDINGS_WITHOUT_HEADER = 2


@dataclass(frozen=True)
class _ExamHit:
    doc: PreparedDoc
    segment: Segment
    date: str | None


def _find_exam_hit(doc: PreparedDoc) -> _ExamHit | None:
    findings: set[str] = set()
    header_segment: Segment | None = None
    first_finding_segment: Segment | None = None

    for segment in doc.segments:
        if header_segment is None and EXAM_SECTION.search(segment.text):
            header_segment = segment
        for match in EXAM_FINDING.finditer(segment.text):
            if is_negated(segment.text, match.start(), match.end()):
                continue
            findings.add(match.group(0).lower())
            if first_finding_segment is None:
                first_finding_segment = segment

    segment = header_segment or first_finding_segment
    if segment is None:
        return None
    if header_segment is None and len(findings) < MIN_FINDINGS_WITHOUT_HEADER:
        return None

    return _ExamHit(doc=doc, segment=segment, date=doc.date)


def extract_recent_physical_exam(
    docs: list[PreparedDoc],
    as_of_date: str | None,
    recency_window_days: int,
) -> Finding[bool]:
    """True only when a documented exam can be *dated* inside the recency window.

    An undated or stale exam stays False. A stale exam is still cited, with its
    age, so the Orchestrator can tell the HCP exactly what to upload.
    """
    hits = [hit for hit in (_find_exam_hit(doc) for doc in docs) if hit is not None]

    if not hits:
        return Finding(
            value=False,
            trace=[
                TraceEntry(
                    field=FIELD,
                    decision="no documented physical examination found in the supplied records",
                )
            ],
        )

    if as_of_date is None:
        return Finding(
            value=False,
            trace=[
                TraceEntry(
                    field=FIELD,
                    decision=(
                        "physical exam found but no reference date available; "
                        "recency cannot be established"
                    ),
                    source_id=hits[0].doc.source_id,
                )
            ],
        )

    dated = sorted(
        ((hit, days_between(hit.date, as_of_date)) for hit in hits if hit.date is not None),
        key=lambda pair: pair[1],
    )

    if not dated:
        return Finding(
            value=False,
            trace=[
                TraceEntry(
                    field=FIELD,
                    decision=(
                        "physical exam found but it is undated; recency cannot be established"
                    ),
                    source_id=hits[0].doc.source_id,
                )
            ],
        )

    newest, age_days = dated[0]

    if age_days <= recency_window_days:
        return Finding(
            value=True,
            citations=[
                cite(
                    newest.doc,
                    newest.segment,
                    f"Physical examination documented {age_days} days before {as_of_date}",
                )
            ],
            trace=[
                TraceEntry(
                    field=FIELD,
                    decision=(
                        f"exam dated {newest.date} is within the "
                        f"{recency_window_days}-day window"
                    ),
                    source_id=newest.doc.source_id,
                    page=newest.segment.page,
                    accepted=True,
                )
            ],
        )

    return Finding(
        value=False,
        citations=[
            cite(
                newest.doc,
                newest.segment,
                f"Most recent documented physical examination is {age_days} days old "
                f"(outside the {recency_window_days}-day recency window)",
            )
        ],
        trace=[
            TraceEntry(
                field=FIELD,
                decision=(
                    f"newest exam dated {newest.date} is {age_days} days old, "
                    f"outside the {recency_window_days}-day window"
                ),
                source_id=newest.doc.source_id,
                page=newest.segment.page,
            )
        ],
    )
