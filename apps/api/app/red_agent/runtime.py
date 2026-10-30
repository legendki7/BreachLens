from uuid import uuid4

from app.models.registry import ModelProvider, TargetModel
from app.red_agent.contracts import AttackerModelConfiguration


def build_attacker_gateway_model(
    configuration: AttackerModelConfiguration,
) -> TargetModel:
    """Create a transient gateway model; no registry row is persisted."""

    provider_id = uuid4()
    provider = ModelProvider(
        id=provider_id,
        name=configuration.provider,
        slug=f"runtime-attacker-{provider_id}",
        provider_type=configuration.provider,
        is_active=True,
    )
    return TargetModel(
        id=uuid4(),
        provider=provider,
        provider_id=provider_id,
        display_name=configuration.canonical_model_id,
        canonical_model_id=configuration.canonical_model_id,
        description="Transient Red Agent attacker-model execution configuration",
        configuration=dict(configuration.provider_configuration),
        third_party=configuration.third_party,
        is_active=True,
    )
