"""Sentence-scoped negation and hedging detection.

The agent must never report a positive finding that the record negates, so
every extractor runs its candidate matches through :func:`is_negated` and
:func:`is_speculative` before counting them.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

#: Clause boundaries stop a negation reaching across
#: ("denies pain, but instability persists").
CLAUSE_BOUNDARY = re.compile(
    r"\b(?:but|however|although|though|otherwise|whereas|despite|except)\b|;",
    re.IGNORECASE,
)

PRE_NEGATION: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bno\b",
        r"\bnot\b",
        r"\bwithout\b",
        r"\bdenies?\b",
        r"\bdenied\b",
        r"\bnegative (?:for|study)\b",
        r"\babsent\b",
        r"\babsence of\b",
        r"\bruled? out\b",
        r"\bfree of\b",
        r"\bnever\b",
        r"\bunremarkable\b",
        r"\bno longer\b",
        r"\bfail(?:s|ed)? to (?:show|demonstrate|reveal|identify)\b",
    )
)

POST_NEGATION: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\W*(?:is|was|were|are|has been|have been)?\s*(?:not\s+)?(?:absent|negative|resolved)\b",
        r"^\W*(?:is|was|were|are)\s+not\b",
        r"\bnot\s+(?:seen|noted|observed|present|identified|appreciated|demonstrated"
        r"|visualized|documented|reported)\b",
        r"\bwas (?:denied|ruled out)\b",
    )
)

#: Phrases where a negation cue attaches to the *outcome* rather than the
#: entity: "did not respond to NSAIDs" still means NSAIDs were tried.
NEGATION_EXEMPTIONS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:no|not|without)\s+(?:\w+\s+){0,2}"
        r"(?:respon(?:se|d|ding)|relief|improv(?:ement|ing|ed)|benefit|resolution"
        r"|tolera(?:nce|ting|te)|help|change|success)\b",
        re.IGNORECASE,
    ),
)

#: Forward-looking, hypothetical, or hedged language.
SPECULATION: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:recommend(?:s|ed|ation)?|advis(?:e|ed)|suggest(?:s|ed)?)\b",
        r"\b(?:plan|planned|planning|scheduled?|awaiting|pending)\b",
        r"\b(?:will|would|should|may|might|consider(?:ing)?)\b",
        r"\b(?:order(?:s|ed)?|refer(?:red|ral)? for|to (?:evaluate|assess|rule out)"
        r"|rule out|r/o)\b",
        r"\b(?:if|unless)\b",
        # Hedged findings are not documented facts.
        r"\b(?:suspect(?:ed|s|ion)?|presumed|possible|probable|questionable"
        r"|concern(?:ing)? for|cannot (?:be )?exclude[d]?|differential)\b",
    )
)

_PRE_WINDOW = 60
_POST_WINDOW = 40


def _last_boundary_end(text: str) -> int:
    end = -1
    for match in CLAUSE_BOUNDARY.finditer(text):
        end = match.end()
    return end


def _first_boundary_start(text: str) -> int:
    match = CLAUSE_BOUNDARY.search(text)
    return match.start() if match else -1


def is_negated(
    sentence: str,
    start: int,
    end: int,
    exemptions: Sequence[re.Pattern[str]] = (),
) -> bool:
    """True when the match at ``[start, end)`` sits in a negated context."""
    pre = sentence[max(0, start - _PRE_WINDOW) : start]
    boundary = _last_boundary_end(pre)
    if boundary >= 0:
        pre = pre[boundary:]

    post = sentence[end : end + _POST_WINDOW]
    post_boundary = _first_boundary_start(post)
    if post_boundary >= 0:
        post = post[:post_boundary]

    for pattern in (*NEGATION_EXEMPTIONS, *exemptions):
        if pattern.search(pre):
            return False

    return any(pattern.search(pre) for pattern in PRE_NEGATION) or any(
        pattern.search(post) for pattern in POST_NEGATION
    )


def clause_around(sentence: str, start: int, end: int) -> str:
    """The clause surrounding a match, bounded by conjunctions and semicolons.

    Lets an extractor judge "completed 8 weeks of PT; will continue monthly" on
    the clause that actually contains the number.
    """
    before = sentence[:start]
    after = sentence[end:]

    boundary = _last_boundary_end(before)
    left = boundary if boundary >= 0 else 0

    post_boundary = _first_boundary_start(after)
    right = end + post_boundary if post_boundary >= 0 else len(sentence)

    return sentence[left:right].strip()


def is_speculative(sentence: str) -> bool:
    """True when the sentence describes a plan, hedge, or hypothetical."""
    return any(pattern.search(sentence) for pattern in SPECULATION)
