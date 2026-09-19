from __future__ import annotations

import re

from ..text.negation import clause_around, is_negated, is_speculative
from .base import Finding, PreparedDoc, TraceEntry, cite

FIELD = "evidence.nsaid_trial"

NSAID_TERM = re.compile(
    r"\b(?:nsaids?|non-?steroidal anti-?inflammator(?:y|ies)|ibuprofen|naproxen"
    r"|meloxicam|diclofenac|celecoxib|indomethacin|ketorolac|etodolac|nabumetone"
    r"|piroxicam|motrin|advil|aleve|celebrex|mobic|toradol)\b",
    re.IGNORECASE,
)

#: An allergy or contraindication is not a therapeutic trial.
NON_TRIAL_CONTEXT = re.compile(
    r"\b(?:allerg(?:y|ic|ies)|contraindicat(?:ed|ion)|intoleran(?:t|ce)"
    r"|adverse reaction|hypersensitiv(?:e|ity)|avoid(?:s|ed)?|hold|withhold)\b",
    re.IGNORECASE,
)

#: "Failed NSAIDs" and "no relief from ibuprofen" both mean the drug was tried.
TRIAL_EXEMPTIONS = (
    re.compile(r"\b(?:fail(?:ed|ure)|refractory|unresponsive|ineffective)\b", re.IGNORECASE),
)


def extract_nsaid_trial(docs: list[PreparedDoc]) -> Finding[bool]:
    trace: list[TraceEntry] = []

    for doc in docs:
        for segment in doc.segments:
            for match in NSAID_TERM.finditer(segment.text):
                clause = clause_around(segment.text, match.start(), match.end())

                if NON_TRIAL_CONTEXT.search(clause):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="NSAID mention is an allergy or contraindication, not a trial",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=clause,
                        )
                    )
                    continue

                if is_negated(segment.text, match.start(), match.end(), TRIAL_EXEMPTIONS):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="NSAID mention rejected as negated",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=clause,
                        )
                    )
                    continue

                if is_speculative(clause):
                    trace.append(
                        TraceEntry(
                            field=FIELD,
                            decision="NSAID mention rejected as planned rather than attempted",
                            source_id=doc.source_id,
                            page=segment.page,
                            matched_text=clause,
                        )
                    )
                    continue

                trace.append(
                    TraceEntry(
                        field=FIELD,
                        decision="NSAID trial accepted",
                        source_id=doc.source_id,
                        page=segment.page,
                        matched_text=clause,
                        accepted=True,
                    )
                )
                return Finding(
                    value=True,
                    citations=[cite(doc, segment, "NSAID trial documented")],
                    trace=trace,
                )

    trace.append(TraceEntry(field=FIELD, decision="no documented NSAID trial found"))
    return Finding(value=False, trace=trace)
