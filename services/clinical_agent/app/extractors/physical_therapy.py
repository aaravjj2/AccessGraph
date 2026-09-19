from __future__ import annotations

import re
from dataclasses import dataclass

from ..text.negation import clause_around, is_negated, is_speculative
from ..text.segment import Segment
from .base import Finding, PreparedDoc, TraceEntry, cite

FIELD = "evidence.physical_therapy_weeks"

WORD_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

_NUMBER = r"\d{1,3}|" + "|".join(WORD_NUMBERS)
_UNIT = r"weeks?|wks?|months?|mos?"

#: "6-8 weeks", "6 to 8 weeks" — we take the lower bound.
RANGE = re.compile(
    r"\b(" + _NUMBER + r")\s*(?:-|\u2013|to)\s*(" + _NUMBER + r")\s*(" + _UNIT + r")\b",
    re.IGNORECASE,
)
#: "8 weeks", "eight-week course", "12 wks".
DURATION = re.compile(r"\b(" + _NUMBER + r")[\s-]*(" + _UNIT + r")\b", re.IGNORECASE)

PT_CONTEXT = re.compile(
    r"\b(?:physical therapy|physiotherapy|rehabilitation|rehab|therapy program"
    r"|formal therapy|conservative (?:therapy|treatment|management|care))\b",
    re.IGNORECASE,
)
#: "PT" is physical therapy only in capitals; lowercase "pt" means patient.
PT_ABBREVIATION = re.compile(r"\bPT\b")

COMPLETION_CUE = re.compile(
    r"\b(?:completed?|finished|underwent|undergone|attended|participated"
    r"|status[- ]post|s/p|has had|have had|received|to date|for the (?:past|last)"
    r"|over the (?:past|last)|documented)\b",
    re.IGNORECASE,
)

WEEKS_PER_MONTH = 4


@dataclass(frozen=True)
class _Candidate:
    weeks: int
    doc: PreparedDoc
    segment: Segment


def _parse_number(token: str) -> int | None:
    lowered = token.lower()
    if lowered in WORD_NUMBERS:
        return WORD_NUMBERS[lowered]
    return int(lowered) if lowered.isdigit() else None


def _to_weeks(value: int, unit: str) -> int:
    return value * WEEKS_PER_MONTH if unit.lower().startswith("mo") else value


def _has_pt_context(sentence: str) -> bool:
    return bool(PT_CONTEXT.search(sentence)) or bool(PT_ABBREVIATION.search(sentence))


def extract_physical_therapy_weeks(docs: list[PreparedDoc]) -> Finding[int]:
    """Longest *documented* course of physical therapy, in weeks.

    Planned or recommended courses do not count; months convert at a
    conservative 4 weeks per month.
    """
    trace: list[TraceEntry] = []
    candidates: list[_Candidate] = []

    for doc in docs:
        for segment in doc.segments:
            if not _has_pt_context(segment.text):
                continue

            consumed: list[tuple[int, int]] = []

            def evaluate(weeks: int | None, start: int, end: int, seg: Segment = segment) -> None:
                if weeks is None:
                    return

                if is_negated(seg.text, start, end):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision=f"rejected {weeks} weeks as negated",
                            source_id=doc.source_id,
                            page=seg.page,
                            matched_text=seg.text,
                        )
                    )
                    return

                clause = clause_around(seg.text, start, end)
                if not COMPLETION_CUE.search(clause) and is_speculative(clause):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision=f"rejected {weeks} weeks as planned rather than completed",
                            source_id=doc.source_id,
                            page=seg.page,
                            matched_text=clause,
                        )
                    )
                    return

                candidates.append(_Candidate(weeks=weeks, doc=doc, segment=seg))
                trace.append(
                    TraceEntry(
                        field=FIELD,
                        decision=f"accepted {weeks} documented weeks",
                        source_id=doc.source_id,
                        page=seg.page,
                        matched_text=clause,
                        accepted=True,
                    )
                )

            for match in RANGE.finditer(segment.text):
                low = _parse_number(match.group(1))
                consumed.append((match.start(), match.end()))
                evaluate(
                    None if low is None else _to_weeks(low, match.group(3)),
                    match.start(),
                    match.end(),
                )

            for match in DURATION.finditer(segment.text):
                if any(start <= match.start() and match.end() <= end for start, end in consumed):
                    continue
                value = _parse_number(match.group(1))
                evaluate(
                    None if value is None else _to_weeks(value, match.group(2)),
                    match.start(),
                    match.end(),
                )

    if not candidates:
        trace.append(
            TraceEntry(
                field=FIELD,
                decision="no documented physical therapy duration found; defaulting to 0",
            )
        )
        return Finding(value=0, trace=trace)

    # max() keeps the first of any tie, so document order breaks ties.
    winner = max(candidates, key=lambda candidate: candidate.weeks)
    return Finding(
        value=winner.weeks,
        citations=[
            cite(winner.doc, winner.segment, f"{winner.weeks} weeks physical therapy completed")
        ],
        trace=trace,
    )
