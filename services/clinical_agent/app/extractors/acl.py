"""Shared ACL vocabulary used by the diagnosis and MRI extractors."""

from __future__ import annotations

import re

ACL_TERM_SRC = r"\b(?:acl|a\.c\.l\.|anterior cruciate ligament)\b"
TEAR_TERM_SRC = (
    r"\b(?:tear|torn|rupture[d]?|disruption|disrupted|discontinuity"
    r"|complete tear|full[- ]thickness tear)\b"
)

#: "Complete tear of the ACL", "ACL rupture", "torn anterior cruciate ligament".
ACL_TEAR = re.compile(
    "(?:" + ACL_TERM_SRC + r")\s*(?:\w+\s+){0,3}?(?:" + TEAR_TERM_SRC + ")"
    "|"
    "(?:" + TEAR_TERM_SRC + r")\s*(?:\w+\s+){0,4}?(?:" + ACL_TERM_SRC + ")",
    re.IGNORECASE,
)

#: Language that marks a radiology statement as an actual finding.
CONFIRMATION_TERM = re.compile(
    r"\b(?:demonstrat(?:es|ed|ing)|show(?:s|ed|ing)?|reveal(?:s|ed|ing)?"
    r"|confirm(?:s|ed|ing)?|consistent with|compatible with|evidence of|noted"
    r"|identified|seen|visualized|impression|findings?|there is|diagnos(?:is|ed)"
    r"|positive for)\b",
    re.IGNORECASE,
)

#: Canonical diagnosis string for the shared contract.
ACL_DIAGNOSIS = "ACL tear"
