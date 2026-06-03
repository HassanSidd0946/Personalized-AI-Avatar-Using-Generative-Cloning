"""
text_cleaner.py - TTS Text Pre-processing Utility
Location : MODAL/text_cleaner.py

Cleans raw text before passing to XTTS-v2 to prevent
hallucination, mumbling, or crashes on emojis/URLs/special chars.
"""

import re
from dataclasses import dataclass, field
import emoji


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CleanResult:
    original: str
    cleaned: str
    steps: list[str] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        return self.original != self.cleaned

    @property
    def char_delta(self) -> int:
        return len(self.original) - len(self.cleaned)

    def summary(self) -> str:
        if not self.was_modified:
            return "  Text was already clean - no changes made."
        lines = [f"  Changes applied ({self.char_delta} chars removed):"]
        for step in self.steps:
            lines.append(f"    * {step}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cleaning steps
# ---------------------------------------------------------------------------

def _remove_emojis(text: str) -> tuple[str, str | None]:
    # Uses the `emoji` library to strip all Unicode emoji characters
    cleaned = emoji.replace_emoji(text, replace="")
    return (cleaned, "Emojis removed") if cleaned != text else (cleaned, None)


def _remove_urls(text: str) -> tuple[str, str | None]:
    # Matches: http://..., https://..., www....
    # https?     = http or https
    # ://        = literal colon-slash-slash
    # S+         = everything until next whitespace (full URL)
    # www\\.S+   = www. without scheme
    pattern = r"https?://(?:www\.)?\S+|www\.\S+"
    cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return (cleaned, "URLs removed") if cleaned != text else (cleaned, None)


def _remove_emails(text: str) -> tuple[str, str | None]:
    # [a-zA-Z0-9._%+-]+  = local part before @
    # @                   = literal @
    # [a-zA-Z0-9.-]+      = domain
    # \.[a-zA-Z]{2,}      = TLD like .com .pk .io
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    cleaned = re.sub(pattern, "", text)
    return (cleaned, "Email addresses removed") if cleaned != text else (cleaned, None)


def _remove_special_characters(text: str) -> tuple[str, str | None]:
    # WHITELIST approach using negated character class [^...]
    # Keep:  a-z A-Z 0-9 . , ? ! ' - and whitespace
    # Strip: @ # $ % ^ & * [ ] { } | \ / < > ~ ` and everything else
    pattern = r"[^a-zA-Z0-9.,?!'\-\s]"
    cleaned = re.sub(pattern, "", text)
    return (cleaned, "Special characters stripped") if cleaned != text else (cleaned, None)


def _normalize_whitespace(text: str) -> tuple[str, str | None]:
    # \s+ matches one or more whitespace chars: space, tab, newline, carriage return
    # Replaces all of them with a single space, then strips ends
    # CRITICAL for XTTS-v2: newlines mid-sentence cause mumbling/hallucination
    cleaned = re.sub(r"\s+", " ", text).strip()
    return (cleaned, "Whitespace normalized (newlines/tabs collapsed)") if cleaned != text else (cleaned, None)


# ---------------------------------------------------------------------------
# Ordered pipeline — sequence matters
# ---------------------------------------------------------------------------
# 1. Emojis first  (they leave Unicode residue if processed after special chars)
# 2. URLs/emails   (before special char pass to avoid partial stripping)
# 3. Special chars (whitelist pass)
# 4. Whitespace    (clean up gaps left by previous removals)

_CLEANING_STEPS = [
    _remove_emojis,
    _remove_urls,
    _remove_emails,
    _remove_special_characters,
    _normalize_whitespace,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_text(text: str) -> CleanResult:
    """
    Run all cleaning steps and return a CleanResult with audit trail.

    Example:
        result = clean_text("Hello! Check https://example.com now!")
        print(result.cleaned)   # "Hello! Check now!"
        print(result.summary()) # what was removed
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")

    current = text
    logs = []

    for step_fn in _CLEANING_STEPS:
        current, log = step_fn(current)
        if log:
            logs.append(log)

    return CleanResult(original=text, cleaned=current, steps=logs)


def clean_text_simple(text: str) -> str:
    """Returns only the cleaned string. Use when audit trail is not needed."""
    return clean_text(text).cleaned