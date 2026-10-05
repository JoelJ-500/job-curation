"""Deterministic text normalisation.

Converts raw document text into a lightweight, meaning-dense form before it is
sent to the LLM: normalises whitespace, drops lines with no semantic value
(page numbers, rules, boilerplate), and collapses blank lines. No LLM calls, so
it is cheap and predictable.
"""

import re

_PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d+\s*(of\s*\d+)?\s*$", re.IGNORECASE)
_RULE_LINE = re.compile(r"^[\s\-_=*#~.·•]+$")
_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+\n")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_NOISE_PHRASES = re.compile(
    r"^\s*(references available (up)?on request\.?|confidential(ity)? notice.*)\s*$",
    re.IGNORECASE,
)
_HAS_ALPHANUMERIC = re.compile(r"[A-Za-z0-9]")


def _is_meaningful(line: str) -> bool:
    """Return False for lines that carry no semantic meaning."""
    stripped = line.strip()
    if not stripped:
        return False
    if _PAGE_NUMBER.match(stripped):
        return False
    if _RULE_LINE.match(stripped):
        return False
    if _NOISE_PHRASES.match(stripped):
        return False
    if not _HAS_ALPHANUMERIC.search(stripped):
        return False
    return True


def clean_text(raw_text: str, preserve_indentation: bool = False) -> str:
    """Normalise and strip meaningless content from extracted document text.

    `preserve_indentation` keeps leading whitespace and internal spacing (used
    for code files, where indentation is meaningful).
    """
    if not raw_text:
        return ""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(
        character
        for character in text
        if character in ("\n", "\t") or ord(character) >= 32
    )

    kept_lines = [line.rstrip() for line in text.split("\n") if _is_meaningful(line)]
    cleaned = "\n".join(kept_lines)

    if not preserve_indentation:
        cleaned = _MULTIPLE_SPACES.sub(" ", cleaned)

    cleaned = _TRAILING_SPACES.sub("\n", cleaned)
    cleaned = _MULTIPLE_BLANK_LINES.sub("\n\n", cleaned)
    return cleaned.strip()
