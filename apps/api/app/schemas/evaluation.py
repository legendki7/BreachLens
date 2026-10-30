from __future__ import annotations

from typing import Annotated

from pydantic import (
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.evaluation.contracts import (
    JudgeModelConfiguration,
    PriorEvaluationTurn,
    TrustedEvaluationContext,
)
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailExecutionReport,
    contains_credentials,
)
from app.schemas.common import DomainSchema

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvaluationTestRequest(DomainSchema):
    scenario_slug: NonBlankString
    attack_pattern_slug: NonBlankString
    attack_prompt: NonBlankString
    target_response: NonBlankString | None = None
    target_was_called: bool
    target_system_prompt: NonBlankString | None = None
    input_guardrail_report: GuardrailExecutionReport | None = None
    output_guardrail_report: GuardrailExecutionReport | None = None
    turn_number: int = Field(gt=0)
    prior_turns: tuple[PriorEvaluationTurn, ...] = ()
    trusted_context: TrustedEvaluationContext | None = None
    evaluation_context: dict[str, JsonValue] = Field(default_factory=dict)
    judge_model: JudgeModelConfiguration | None = None

    @field_validator("evaluation_context")
    @classmethod
    def reject_context_credentials(
        cls,
        value: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if contains_credentials(value):
            raise ValueError("Evaluation context cannot contain credentials")
        return value

    @model_validator(mode="after")
    def validate_interaction_state(self) -> EvaluationTestRequest:
        if not self.target_was_called and self.target_response is not None:
            raise ValueError("A target response requires target execution")
        if not self.target_was_called and self.output_guardrail_report is not None:
            raise ValueError("Output guardrails require target execution")
        if (
            self.input_guardrail_report is not None
            and self.input_guardrail_report.stage.value != "input"
        ):
            raise ValueError("Input guardrail report has the wrong stage")
        if (
            self.output_guardrail_report is not None
            and self.output_guardrail_report.stage.value != "output"
        ):
            raise ValueError("Output guardrail report has the wrong stage")
        if (
            self.input_guardrail_report is not None
            and self.input_guardrail_report.final_decision
            is GuardrailDecision.BLOCK
            and self.target_was_called
        ):
            raise ValueError("Target cannot be called after an input guardrail block")
        return self
