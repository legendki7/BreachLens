import argparse
import asyncio

from app.guardrails.contracts import (
    GuardrailPolicyContext,
    GuardrailRequest,
    GuardrailScenarioContext,
    GuardrailStage,
)
from app.guardrails.dependencies import get_guardrail_engine
from app.guardrails.exceptions import GuardrailError
from app.reference_data import POLICY_PROFILES, SCENARIOS


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test content against guardrails without target-model generation.",
    )
    parser.add_argument("--stage", choices=["input", "output"], required=True)
    parser.add_argument("--policy", choices=["strict", "moderate", "permissive"], required=True)
    parser.add_argument("--scenario", default="jailbreak")
    parser.add_argument("--content", required=True)
    parser.add_argument(
        "--adapter",
        action="append",
        choices=["native", "nemo"],
        dest="adapters",
        help="Adapter to run; repeat for multiple adapters (default: native)",
    )
    return parser.parse_args()


async def run() -> int:
    arguments = parse_arguments()
    scenario = next(
        (item for item in SCENARIOS if item.slug == arguments.scenario),
        None,
    )
    if scenario is None:
        print(f"Unknown scenario: {arguments.scenario}")
        return 2
    profile = next(
        (item for item in POLICY_PROFILES if item.slug == arguments.policy),
        None,
    )
    if profile is None:
        print(f"Unknown policy: {arguments.policy}")
        return 2

    adapters = tuple(arguments.adapters or ["native"])
    request = GuardrailRequest(
        stage=GuardrailStage(arguments.stage),
        content=arguments.content,
        scenario=GuardrailScenarioContext(
            name=scenario.name,
            slug=scenario.slug,
            description=scenario.description,
        ),
        policy_profile=GuardrailPolicyContext(
            name=profile.name,
            slug=profile.slug,
            strictness_level=profile.strictness_level,
            configuration={"nemo_enabled": "nemo" in adapters},
        ),
    )
    try:
        report = await get_guardrail_engine().execute(request, adapters)
    except GuardrailError as exc:
        print(str(exc))
        return 1

    print(report.model_dump_json(indent=2))
    return 0 if report.should_continue else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
