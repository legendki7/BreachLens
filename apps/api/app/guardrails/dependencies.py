from functools import lru_cache

from app.guardrails.adapters import NativeGuardrailAdapter, NeMoGuardrailAdapter
from app.guardrails.engine import GuardrailEngine


@lru_cache
def get_guardrail_engine() -> GuardrailEngine:
    return GuardrailEngine(
        (
            NativeGuardrailAdapter(),
            NeMoGuardrailAdapter(),
        )
    )
