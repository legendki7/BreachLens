from app.evaluation.contracts import (
    BlueEvaluationRequest,
    BlueEvaluationResult,
    EvaluationOutcome,
    JudgeModelConfiguration,
    JudgeStructuredOutput,
    ModelJudgmentResult,
)
from app.evaluation.exceptions import (
    JudgeGenerationError,
    JudgeOutputValidationError,
)
from app.evaluation.output_parser import JudgeOutputParser
from app.evaluation.prompt_builder import JudgePromptBuilder, MODEL_EVIDENCE_SOURCES
from app.evaluation.rubrics.types import ScenarioRubric
from app.evaluation.runtime import build_judge_gateway_model
from app.model_gateway.exceptions import ModelGatewayError
from app.model_gateway.gateway import ModelGateway


class RubricJudge:
    def __init__(
        self,
        gateway: ModelGateway,
        prompt_builder: JudgePromptBuilder | None = None,
        output_parser: JudgeOutputParser | None = None,
    ) -> None:
        self._gateway = gateway
        self._prompt_builder = prompt_builder or JudgePromptBuilder()
        self._output_parser = output_parser or JudgeOutputParser()

    async def judge(
        self,
        rubric: ScenarioRubric,
        request: BlueEvaluationRequest,
        blue_result: BlueEvaluationResult,
        judge_model: JudgeModelConfiguration,
    ) -> ModelJudgmentResult:
        if not request.target_was_called or request.target_response is None:
            raise JudgeOutputValidationError()

        model_request = self._prompt_builder.build(
            rubric,
            request,
            blue_result,
            temperature=judge_model.generation.temperature,
            max_tokens=judge_model.generation.max_tokens,
        )
        runtime_model = build_judge_gateway_model(judge_model)
        try:
            generation = await self._gateway.generate(runtime_model, model_request)
        except ModelGatewayError as exc:
            raise JudgeGenerationError(exc.provider_type) from exc

        output = self._output_parser.parse(generation.content)
        self._validate_output(output, request, blue_result)
        return ModelJudgmentResult(
            model_outcome=output.model_outcome,
            model_attack_success_score=output.model_attack_success_score,
            confidence=output.confidence,
            judge_reason=output.reason,
            evidence=tuple(
                item for item in blue_result.evidence
                if item.source in MODEL_EVIDENCE_SOURCES
            ),
            rubric_id=rubric.rubric_id,
            rubric_version=rubric.version,
            judge_model_id=generation.model_id,
            judge_provider=generation.provider,
            latency_ms=generation.latency_ms,
            metadata={
                "judge_role": judge_model.role,
                "judge_third_party": judge_model.third_party,
                "finish_reason": generation.finish_reason,
                "input_tokens": generation.input_tokens,
                "output_tokens": generation.output_tokens,
                "total_tokens": generation.total_tokens,
                "judge_evidence_codes": list(output.evidence_codes),
                "chain_of_thought_stored": False,
            },
        )

    @staticmethod
    def _validate_output(
        output: JudgeStructuredOutput,
        request: BlueEvaluationRequest,
        blue_result: BlueEvaluationResult,
    ) -> None:
        if output.model_outcome is EvaluationOutcome.BLOCKED_BY_GUARDRAIL:
            raise JudgeOutputValidationError()
        evidence_codes = {
            evidence.code for evidence in blue_result.evidence
            if evidence.source in MODEL_EVIDENCE_SOURCES
        }
        if any(code not in evidence_codes for code in output.evidence_codes):
            raise JudgeOutputValidationError()
