from uuid import uuid4

from app.evaluation.contracts import JudgeModelConfiguration
from app.models.registry import ModelProvider, TargetModel


def build_judge_gateway_model(
    configuration: JudgeModelConfiguration,
) -> TargetModel:
    """Create a transient Judge Model execution object; persist nothing."""

    provider_id = uuid4()
    provider = ModelProvider(
        id=provider_id,
        name=configuration.provider,
        slug=f"runtime-judge-{provider_id}",
        provider_type=configuration.provider,
        is_active=True,
    )
    return TargetModel(
        id=uuid4(),
        provider=provider,
        provider_id=provider_id,
        display_name=configuration.canonical_model_id,
        canonical_model_id=configuration.canonical_model_id,
        description="Transient rubric Judge Model execution configuration",
        configuration=dict(configuration.provider_configuration),
        third_party=configuration.third_party,
        is_active=True,
    )
