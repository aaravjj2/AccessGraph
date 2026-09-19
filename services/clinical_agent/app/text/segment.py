"""Splits raw document text into page-aware sentences for provenance."""

from __future__ import annotations

import re
from dataclasses import dataclass

#: A line that is nothing but a page marker, e.g. "Page 2" or "--- Page 2 ---".
PAGE_HEADER = re.compile(
    r"^[ \t]*(?:[-=]{2,}\s*)?page\s+(\d+)(?:\s*of\s*\d+)?\s*(?:[-=]{2,})?[ \t]*$",
    re.IGNORECASE,
)

_LINE_BREAK = re.compile(r"\r?\n")
_LINE_BREAKS = re.compile(r"\r?\n+")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")


@dataclass(frozen=True)
class Segment:
    """A sentence, tagged with the page it came from."""

    text: str
    #: 1-based page number.
    page: int
    #: 0-based position within the document.
    index: int


def split_pages(text: str) -> list[tuple[int, str]]:
    """Returns ``(page_number, page_text)`` pairs."""
    if "\f" in text:
        return [
            (number, page_text)
            for number, page_text in enumerate(text.split("\f"), start=1)
            if page_text.strip()
        ]

    pages: list[tuple[int, str]] = []
    current_page = 1
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        if any(line.strip() for line in current_lines):
            pages.append((current_page, "\n".join(current_lines)))
        current_lines = []

    for line in _LINE_BREAK.split(text):
        marker = PAGE_HEADER.match(line)
        if marker:
            flush()
            current_page = int(marker.group(1))
            continue
        current_lines.append(line)

    flush()
    return pages or [(1, text)]


def _split_sentences(text: str) -> list[str]:
    """Clinical notes mix prose with bulleted lines, so break on newlines first."""
    sentences: list[str] = []
    for line in _LINE_BREAKS.split(text):
        for sentence in _SENTENCE_BREAK.split(line):
            stripped = sentence.strip()
            if stripped:
                sentences.append(stripped)
    return sentences


def segment_document(text: str) -> list[Segment]:
    segments: list[Segment] = []
    index = 0
    for page_number, page_text in split_pages(text):
        for sentence in _split_sentences(page_text):
            segments.append(Segment(text=sentence, page=page_number, index=index))
            index += 1
    return segments
