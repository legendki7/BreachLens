from abc import ABC, abstractmethod

from app.guardrails.contracts import GuardrailRequest, GuardrailResult


class GuardrailAdapter(ABC):
    name: str

    @abstractmethod
    async def apply(self, request: GuardrailRequest) -> GuardrailResult:
        """Apply one normalized guardrail stage without orchestrating model calls."""
