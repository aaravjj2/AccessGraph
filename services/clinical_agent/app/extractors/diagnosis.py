from __future__ import annotations

from ..text.negation import is_negated, is_speculative
from .acl import ACL_DIAGNOSIS, ACL_TEAR
from .base import Finding, PreparedDoc, TraceEntry, cite

FIELD = "diagnosis"


def extract_diagnosis(docs: list[PreparedDoc]) -> Finding[str | None]:
    """Reports the canonical diagnosis when a document states an ACL tear as a
    fact. Returns ``None`` rather than guessing."""
    trace: list[TraceEntry] = []

    for doc in docs:
        for segment in doc.segments:
            for match in ACL_TEAR.finditer(segment.text):
                if is_negated(segment.text, match.start(), match.end()):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="ACL tear statement rejected as negated",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=segment.text,
                        )
                    )
                    continue

                if is_speculative(segment.text):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="ACL tear statement rejected as hedged, planned, or hypothetical",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=segment.text,
                        )
                    )
                    continue

                trace.append(
                    TraceEntry(
                        field=FIELD,
                        decision=f"matched ACL tear language in {doc.source_id}",
                        source_id=doc.source_id,
                        page=segment.page,
                        matched_text=segment.text,
                        accepted=True,
                    )
                )
                return Finding(
                    value=ACL_DIAGNOSIS,
                    citations=[cite(doc, segment, f"Diagnosis documented: {ACL_DIAGNOSIS}")],
                    trace=trace,
                )

    trace.append(
        TraceEntry(field=FIELD, decision="no non-negated ACL tear statement found")
    )
    return Finding(value=None, trace=trace)
