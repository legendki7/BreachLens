from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from app.model_gateway.contracts import ModelGenerationRequest, ModelGenerationResult


class ModelProviderAdapter(ABC):
    """Small contract implemented by each external model provider adapter."""

    provider_type: str

    @abstractmethod
    async def generate(
        self,
        model_id: str,
        request: ModelGenerationRequest,
        configuration: Mapping[str, Any],
    ) -> ModelGenerationResult:
        """Execute one normalized generation request."""

    @abstractmethod
    async def health_check(
        self,
        model_id: str,
        configuration: Mapping[str, Any],
    ) -> bool:
        """Report whether the adapter is configured to attempt this model."""

