from functools import lru_cache

from app.core.config import get_settings
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.providers.huggingface import (
    HUGGING_FACE_PROVIDER_TYPE,
    HuggingFaceProviderAdapter,
)


@lru_cache
def get_model_gateway() -> ModelGateway:
    settings = get_settings()
    return ModelGateway(
        {
            HUGGING_FACE_PROVIDER_TYPE: HuggingFaceProviderAdapter(
                token=settings.hf_token,
            )
        }
    )

