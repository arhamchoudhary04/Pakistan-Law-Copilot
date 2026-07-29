"""Deterministic answer-language detection.

The small generation model doesn't reliably honour a soft "reply in the user's
language" instruction, so we detect the language here and pass an explicit per-turn
directive. Order: an explicit request ("answer in Urdu") wins, then Urdu script,
then Roman-Urdu function words vs English.
"""

from __future__ import annotations

import re
from typing import Literal

Language = Literal["english", "urdu", "roman-urdu"]

# Urdu / Arabic script blocks (incl. Arabic presentation forms).
_URDU_SCRIPT_RE = re.compile(
    "[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]"
)

# An explicit request to answer in a named language. Anchored on a request verb so
# incidental mentions ("what are my rights in Urdu-speaking areas") don't trigger it.
_REQUEST_VERB = (
    r"(?:answer|reply|respond|explain|translate|write|jawab|jwab|jawaab|bata|batao|"
    r"bta|btao|likho|likh|samjhao|samjha|dijiye|dena)"
)
_LANG = r"(urdu|english|angrezi|angreji|inglish)"
_OVERRIDE_RE = re.compile(
    rf"{_REQUEST_VERB}[^.?!]*?\b{_LANG}\b|\b{_LANG}\b[^.?!]*?{_REQUEST_VERB}",
    re.IGNORECASE,
)

# Roman-Urdu function words (Urdu written in Latin letters). Chosen to avoid common
# English words so English text is not misclassified as Roman Urdu.
_ROMAN_URDU_MARKERS = frozenset(
    {
        "kya", "kia", "kiya", "hai", "hain", "mujhe", "mujhy", "mera", "meri", "mere",
        "kaise", "kaisay", "kese", "kesay", "kaisa", "liye", "liay", "kliye", "nahi",
        "nahin", "karta", "karti", "karna", "krna", "krne", "hota", "hoti", "mein",
        "kaun", "kon", "agar", "aur", "haq", "sakta", "sakti", "chahiye", "chahiaye",
        "kyun", "kyu", "apna", "apni", "apka", "apki", "batao", "bata", "raha", "rahi",
        "gaya", "gayi", "hoga", "hogi", "wala", "wali", "ka", "ki", "ko", "kar",
    }
)


def detect_language(text: str) -> Language:
    """Classify the language a reply should be written in."""
    lowered = text.lower()
    override = _OVERRIDE_RE.search(lowered)
    if override:
        named = (override.group(1) or override.group(2) or "").lower()
        if named == "urdu":
            return "urdu"
        return "english"  # english / angrezi / inglish
    if _URDU_SCRIPT_RE.search(text):
        return "urdu"
    words = set(re.findall(r"[a-z]+", lowered))
    if len(words & _ROMAN_URDU_MARKERS) >= 2:
        return "roman-urdu"
    return "english"


_DIRECTIVES: dict[Language, str] = {
    "english": "Write your entire answer in English.",
    "urdu": (
        "Write your entire answer in Urdu (Urdu/Arabic script). Keep provision names "
        '(e.g. "Article 10A") and the [n] citation markers in English.'
    ),
    "roman-urdu": (
        "Write your entire answer in Roman Urdu (Urdu written in the Latin alphabet, the "
        "way the question is written). Do not use Urdu/Arabic script. Keep provision names "
        '(e.g. "Article 10A") and the [n] citation markers in English.'
    ),
}


def language_directive(text: str) -> str:
    """An explicit per-turn instruction telling the model which language to answer in."""
    return _DIRECTIVES[detect_language(text)]
