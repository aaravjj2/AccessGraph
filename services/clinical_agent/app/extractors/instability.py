from __future__ import annotations

import re
from dataclasses import dataclass

from ..contracts import SourceRef
from ..text.negation import clause_around, is_negated, is_speculative
from .base import Finding, PreparedDoc, TraceEntry, cite

FIELD = "evidence.persistent_instability"

INSTABILITY_TERM = re.compile(
    r"\b(?:instability|unstable|giving[- ]way|gives[- ]way|gives out|giving out"
    r"|buckl(?:ing|es|ed)|laxity|subluxat(?:ion|ing))\b",
    re.IGNORECASE,
)

#: Language establishing the symptom is ongoing rather than a one-off note.
PERSISTENCE_CUE = re.compile(
    r"\b(?:persist(?:s|ent|ing|ed)?|continu(?:es|ed|ing|al)|ongoing|still|remains?"
    r"|recurrent|recurring|chronic|refractory|despite|daily|repeated(?:ly)?"
    r"|unchanged|for (?:the )?(?:past|last)|since)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Hit:
    citation: SourceRef
    persistent: bool
    source_id: str


def extract_persistent_instability(docs: list[PreparedDoc]) -> Finding[bool]:
    """True when the record describes instability as ongoing, or when
    independent documents describe it.

    A lone undated mention is not upgraded to "persistent".
    """
    trace: list[TraceEntry] = []
    hits: list[_Hit] = []

    for doc in docs:
        for segment in doc.segments:
            for match in INSTABILITY_TERM.finditer(segment.text):
                if is_negated(segment.text, match.start(), match.end()):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="instability mention rejected as negated",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=segment.text,
                        )
                    )
                    continue

                clause = clause_around(segment.text, match.start(), match.end())
                if is_speculative(clause):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="instability mention rejected as hypothetical",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=clause,
                        )
                    )
                    continue

                persistent = bool(PERSISTENCE_CUE.search(segment.text))
                hits.append(
                    _Hit(
                        citation=cite(
                            doc,
                            segment,
                            "Persistent knee instability reported"
                            if persistent
                            else "Knee instability documented",
                        ),
                        persistent=persistent,
                        source_id=doc.source_id,
                    )
                )
                trace.append(
                    TraceEntry(
                        field=FIELD,
                        decision=(
                            "instability with persistence cue accepted"
                            if persistent
                            else "instability without persistence cue recorded"
                        ),
                        source_id=doc.source_id,
                        page=segment.page,
                        matched_text=segment.text,
                        accepted=persistent,
                    )
                )

    explicit = next((hit for hit in hits if hit.persistent), None)
    if explicit is not None:
        return Finding(value=True, citations=[explicit.citation], trace=trace)

    distinct_docs = {hit.source_id for hit in hits}
    if len(distinct_docs) >= 2:
        trace.append(
            TraceEntry(
                field=FIELD,
                decision=(
                    f"instability documented across {len(distinct_docs)} documents, "
                    "treated as persistent"
                ),
                accepted=True,
            )
        )
        return Finding(
            value=True, citations=[hit.citation for hit in hits[:2]], trace=trace
        )

    trace.append(
        TraceEntry(
            field=FIELD,
            decision=(
                "single isolated instability mention without persistence cue; "
                "not reported as persistent"
                if hits
                else "no documented knee instability found"
            ),
        )
    )
    return Finding(value=False, trace=trace)
