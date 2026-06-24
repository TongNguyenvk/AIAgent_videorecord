"""
Prompt-injection guard for user supplied job text.

This is a submit-time safety layer. Worker prompts still need their own
role/data separation because API checks can be bypassed by internal callers.
"""

from __future__ import annotations

import re
import unicodedata


class PromptInjectionError(ValueError):
    """Raised when user text looks like a prompt-injection attempt."""


HIGH_RISK_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+"
        r"(instructions?|rules?|prompts?)\b",
        "ignore_previous_instructions",
    ),
    (
        r"\boverride\s+(the\s+)?(system|developer)\s+(prompt|message|instructions?)\b",
        "override_system_prompt",
    ),
    (
        r"\b(reveal|show|print|output|return|dump|extract|display|paste)\s+"
        r"(the\s+)?(system|developer|hidden|internal)\s+(prompt|message|instructions?)\b",
        "extract_system_prompt",
    ),
    (r"\b(jailbreak|dan\s+mode|do\s+anything\s+now)\b", "jailbreak_marker"),
    (
        r"\b(bo\s+qua|lo\s+di|quen)\s+(tat\s+ca\s+)?(huong\s+dan|chi\s+dan)\b",
        "vi_ignore_instructions",
    ),
    (
        r"\b(in|hien\s+thi|tiet\s+lo|xuat|tra\s+ve)\s+(prompt|huong\s+dan|chi\s+dan)\s+he\s+thong\b",
        "vi_extract_system_prompt",
    ),
)

ROLE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bsystem\s+(prompt|message|instructions?)\b", "system_prompt_reference"),
    (r"\bdeveloper\s+(message|instructions?)\b", "developer_message_reference"),
    (r"\b(hidden|internal)\s+(prompt|message|instructions?)\b", "hidden_prompt_reference"),
    (r"\b(prompt|huong\s+dan|chi\s+dan)\s+he\s+thong\b", "vi_system_prompt_reference"),
)

ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(reveal|show|print|output|return|dump|extract|display|paste)\b", "extraction_action"),
    (r"\b(in|hien\s+thi|tiet\s+lo|xuat|tra\s+ve)\b", "vi_extraction_action"),
)

BYPASS_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(ignore|disregard|forget|override|bypass|disable)\b", "bypass_action"),
    (r"\b(bo\s+qua|lo\s+di|quen|ghi\s+de|vo\s+hieu\s+hoa)\b", "vi_bypass_action"),
)


def _fold_ascii(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def _scan(patterns: tuple[tuple[str, str], ...], text: str) -> list[str]:
    signals: list[str] = []
    for pattern, name in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            signals.append(name)
    return signals


def find_prompt_injection_signals(text: str | None) -> list[str]:
    """Return signal names when text looks like a prompt-injection attempt."""
    if not text:
        return []

    haystack = f"{text.lower()}\n{_fold_ascii(text)}"
    signals = _scan(HIGH_RISK_PATTERNS, haystack)

    role_signals = _scan(ROLE_PATTERNS, haystack)
    action_signals = _scan(ACTION_PATTERNS, haystack)
    bypass_signals = _scan(BYPASS_PATTERNS, haystack)

    if role_signals and action_signals:
        signals.extend(role_signals + action_signals)

    if role_signals and bypass_signals:
        signals.extend(role_signals + bypass_signals)

    # Keep order stable while removing duplicates.
    return list(dict.fromkeys(signals))


def validate_no_prompt_injection(text: str | None, field_name: str = "task") -> None:
    signals = find_prompt_injection_signals(text)
    if not signals:
        return

    signal_text = ", ".join(signals[:5])
    raise PromptInjectionError(
        f"{field_name} co dau hieu prompt injection ({signal_text}). "
        "Vui long mo ta muc tieu thao tac thay vi yeu cau bo qua huong dan he thong."
    )
