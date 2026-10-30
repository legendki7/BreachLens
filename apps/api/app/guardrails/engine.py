from time import perf_counter

from app.guardrails.adapter import GuardrailAdapter
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailExecutionReport,
    GuardrailFinding,
    GuardrailFindingSeverity,
    GuardrailRequest,
    GuardrailResult,
)
from app.guardrails.exceptions import (
    GuardrailAdapterUnavailableError,
    GuardrailExecutionError,
)
from app.guardrails.policy import GuardrailPolicyResolver


class GuardrailEngine:
    def __init__(
        self,
        adapters: tuple[GuardrailAdapter, ...],
        policy_resolver: GuardrailPolicyResolver | None = None,
    ) -> None:
        self._adapters = {adapter.name: adapter for adapter in adapters}
        self._adapter_order = tuple(adapter.name for adapter in adapters)
        self._policy_resolver = policy_resolver or GuardrailPolicyResolver()

    async def execute(
        self,
        request: GuardrailRequest,
        adapter_names: tuple[str, ...] | None = None,
    ) -> GuardrailExecutionReport:
        started_at = perf_counter()
        behavior = self._policy_resolver.resolve(request.policy_profile)
        selected_names = self._selected_adapter_names(
            behavior.enabled_adapters,
            adapter_names,
        )

        current_content = request.content
        results: list[GuardrailResult] = []
        for adapter_name in selected_names:
            adapter = self._adapters[adapter_name]
            adapter_request = request.model_copy(update={"content": current_content})
            try:
                raw_result = await adapter.apply(adapter_request)
                self._validate_adapter_result(adapter, adapter_request, raw_result)
                result = self._policy_resolver.enforce(raw_result, behavior)
            except Exception:
                result = self._error_result(adapter_name, adapter_request)

            results.append(result)
            if result.decision in {
                GuardrailDecision.BLOCK,
                GuardrailDecision.ERROR,
            }:
                current_content = None
                break
            if result.processed_content is not None:
                current_content = result.processed_content

        final_decision = self._final_decision(results)
        should_continue = (
            current_content is not None
            and final_decision
            in {
                GuardrailDecision.ALLOW,
                GuardrailDecision.FLAG,
                GuardrailDecision.MODIFY,
            }
        )
        return GuardrailExecutionReport(
            stage=request.stage,
            original_content=request.content,
            final_content=current_content,
            final_decision=final_decision,
            should_continue=should_continue,
            adapter_results=tuple(results),
            total_latency_ms=(perf_counter() - started_at) * 1000,
        )

    def _selected_adapter_names(
        self,
        enabled_names: tuple[str, ...],
        requested_names: tuple[str, ...] | None,
    ) -> tuple[str, ...]:
        if requested_names is not None:
            if not requested_names:
                raise GuardrailAdapterUnavailableError("none")
            for name in requested_names:
                if name not in self._adapters or name not in enabled_names:
                    raise GuardrailAdapterUnavailableError(name)
            requested = set(requested_names)
            return tuple(name for name in self._adapter_order if name in requested)

        for name in enabled_names:
            if name not in self._adapters:
                raise GuardrailAdapterUnavailableError(name)
        return tuple(name for name in self._adapter_order if name in enabled_names)

    @staticmethod
    def _validate_adapter_result(
        adapter: GuardrailAdapter,
        request: GuardrailRequest,
        result: GuardrailResult,
    ) -> None:
        if (
            result.adapter != adapter.name
            or result.stage is not request.stage
            or result.original_content != request.content
        ):
            raise GuardrailExecutionError(adapter.name)

    @staticmethod
    def _error_result(
        adapter_name: str,
        request: GuardrailRequest,
    ) -> GuardrailResult:
        return GuardrailResult(
            stage=request.stage,
            decision=GuardrailDecision.ERROR,
            original_content=request.content,
            processed_content=None,
            triggered_rules=("GUARDRAIL_ADAPTER_ERROR",),
            findings=(
                GuardrailFinding(
                    code="GUARDRAIL_ADAPTER_ERROR",
                    name="Guardrail adapter execution error",
                    severity=GuardrailFindingSeverity.HIGH,
                    description=(
                        "The adapter failed, so the content was not marked safe and "
                        "processing stopped."
                    ),
                ),
            ),
            adapter=adapter_name,
            latency_ms=0,
            metadata={"sanitized_error": True},
        )

    @staticmethod
    def _final_decision(results: list[GuardrailResult]) -> GuardrailDecision:
        if not results:
            return GuardrailDecision.ERROR
        decisions = {result.decision for result in results}
        for decision in (
            GuardrailDecision.ERROR,
            GuardrailDecision.BLOCK,
            GuardrailDecision.MODIFY,
            GuardrailDecision.FLAG,
        ):
            if decision in decisions:
                return decision
        return GuardrailDecision.ALLOW
