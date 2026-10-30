from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenarioRubric:
    rubric_id: str
    version: str
    scenario_slug: str
    objective: str
    safe_behavior: tuple[str, ...]
    breach_conditions: tuple[str, ...]
    partial_compliance_conditions: tuple[str, ...]
    inconclusive_conditions: tuple[str, ...]
    scoring_guidance: tuple[str, ...]
