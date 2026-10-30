import re
from typing import Any

from nemoguardrails.actions import action

INPUT_PATTERNS = (
    re.compile(
        r"\b(?:reveal|show|print|repeat|provide|display|expose)\b.{0,50}"
        r"\b(?:system prompt|hidden instructions?|developer instructions?|"
        r"internal instructions?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:ignore|disregard|forget|override)\b.{0,40}"
        r"\b(?:previous|prior|system|developer|all)\b.{0,30}"
        r"\binstructions?\b",
        re.IGNORECASE | re.DOTALL,
    ),
)
OUTPUT_PATTERNS = (
    re.compile(
        r"\b(?:system prompt|hidden instructions?|developer message)\s*[:=]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:sk-|hf_)[A-Za-z0-9_-]{16,}\b|"
        r"\bBearer\s+[A-Za-z0-9._-]{16,}",
        re.IGNORECASE,
    ),
)


def _context_content(context: dict[str, Any] | None, key: str) -> str:
    if not context:
        return ""
    value = context.get(key, "")
    return value if isinstance(value, str) else ""


@action(is_system_action=True)
async def rta_nemo_check_input(context: dict[str, Any] | None = None) -> bool:
    content = _context_content(context, "user_message")
    return any(pattern.search(content) for pattern in INPUT_PATTERNS)


@action(is_system_action=True)
async def rta_nemo_check_output(context: dict[str, Any] | None = None) -> bool:
    content = _context_content(context, "bot_message")
    return any(pattern.search(content) for pattern in OUTPUT_PATTERNS)
