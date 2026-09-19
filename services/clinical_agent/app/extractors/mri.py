from __future__ import annotations

import re

from ..text.negation import is_negated, is_speculative
from .acl import ACL_TEAR, CONFIRMATION_TERM
from .base import Finding, PreparedDoc, TraceEntry, cite

FIELD = "evidence.mri_confirmed"

MRI_MENTION = re.compile(r"\b(?:mri|magnetic resonance(?: imaging)?|mr imaging)\b", re.IGNORECASE)


def extract_mri_confirmed(docs: list[PreparedDoc]) -> Finding[bool]:
    """Requires an imaging *finding* of an ACL tear, not a mention of an MRI.

    Radiology impressions rarely repeat the word "MRI", so a document
    recognised as an imaging report supplies that context for all its sentences.
    """
    trace: list[TraceEntry] = []

    for doc in docs:
        for segment in doc.segments:
            in_imaging_context = doc.is_imaging or bool(MRI_MENTION.search(segment.text))
            if not in_imaging_context:
                continue

            for match in ACL_TEAR.finditer(segment.text):
                if is_negated(segment.text, match.start(), match.end()):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="ACL tear mention rejected as negated",
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
                            decision="ACL tear mention rejected as planned or hypothetical",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=segment.text,
                        )
                    )
                    continue

                # An imaging report's own findings section is confirmatory by
                # nature; outside one we require explicit confirmation language.
                if not doc.is_imaging and not CONFIRMATION_TERM.search(segment.text):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision=(
                                "ACL tear mention lacks confirmation language "
                                "outside an imaging report"
                            ),
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=segment.text,
                        )
                    )
                    continue

                trace.append(
                    TraceEntry(
                        field=FIELD,
                        decision="imaging finding of ACL tear accepted",
                        source_id=doc.source_id,
                        page=segment.page,
                        matched_text=segment.text,
                        accepted=True,
                    )
                )
                return Finding(
                    value=True,
                    citations=[cite(doc, segment, "MRI confirmed ACL tear")],
                    trace=trace,
                )

    trace.append(TraceEntry(field=FIELD, decision="no imaging finding of ACL tear found"))
    return Finding(value=False, trace=trace)
