"""Text normalization for molecule names.

The normalized form is what we key synonyms on ('have we seen this name?'). It is
deliberately conservative: it does not try to fix chemistry, only to fold trivial
textual variants (case, whitespace, wrapping quotes, unicode form) together.
"""
from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_WRAPPING_QUOTES = "\"'`“”‘’«»"


def normalize_name(name: str) -> str:
    """Return a normalized key for a molecule name.

    Steps: NFKC unicode-normalize → strip → strip wrapping quotes → collapse
    internal whitespace → casefold. Returns '' for blank input.
    """
    if name is None:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).strip()
    # strip matched/again-any wrapping quotes
    s = s.strip(_WRAPPING_QUOTES).strip()
    s = _WHITESPACE.sub(" ", s)
    return s.casefold()


def clean_display_name(name: str) -> str:
    """A light cleanup that preserves case, for storing the human-readable original."""
    if name is None:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).strip()
    s = s.strip(_WRAPPING_QUOTES).strip()
    return _WHITESPACE.sub(" ", s)
