from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from app.guardrails.adapter import GuardrailAdapter
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailFinding,
    GuardrailFindingSeverity,
    GuardrailRequest,
    GuardrailResult,
    GuardrailStage,
)
from app.guardrails.exceptions import (
    GuardrailAdapterUnavailableError,
    GuardrailConfigurationError,
    GuardrailError,
    GuardrailExecutionError,
    UnsupportedGuardrailStageError,
)

DEFAULT_NEMO_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "guardrails" / "nemo"
)


class NeMoRails(Protocol):
    async def check_async(
        self,
        messages: list[dict[str, str]],
        rail_types: list[object] | None = None,
    ) -> object: ...


class NeMoGuardrailAdapter(GuardrailAdapter):
    name = "nemo"

    def __init__(
        self,
        config_path: Path = DEFAULT_NEMO_CONFIG_PATH,
        *,
        rails: NeMoRails | None = None,
        rail_type_factory: Callable[[str], object] | None = None,
    ) -> None:
        self._config_path = config_path
        self._rails = rails
        self._rail_type_factory = rail_type_factory or (lambda value: value)

    async def apply(self, request: GuardrailRequest) -> GuardrailResult:
        if request.stage not in {GuardrailStage.INPUT, GuardrailStage.OUTPUT}:
            raise UnsupportedGuardrailStageError(request.stage)

        started_at = perf_counter()
        try:
            rails = self._rails or self._load_rails()
            role = "user" if request.stage is GuardrailStage.INPUT else "assistant"
            response = await rails.check_async(
                messages=[{"role": role, "content": request.content}],
                rail_types=[self._rail_type_factory(request.stage.value)],
            )
            return self._normalize_result(
                request,
                response,
                latency_ms=(perf_counter() - started_at) * 1000,
            )
        except GuardrailError:
            raise
        except Exception as exc:
            raise GuardrailExecutionError(self.name) from exc

    def _load_rails(self) -> NeMoRails:
        if not self._config_path.is_dir():
            raise GuardrailConfigurationError(
                "Reviewed NeMo guardrail configuration is unavailable"
            )
        try:
            from nemoguardrails import LLMRails, RailsConfig
            from nemoguardrails.rails.llm.options import RailType
        except ImportError as exc:
            raise GuardrailAdapterUnavailableError(self.name) from exc

        try:
            config = RailsConfig.from_path(str(self._config_path))
            self._rails = LLMRails(config)
            self._rail_type_factory = RailType
        except Exception as exc:
            raise GuardrailConfigurationError(
                "Reviewed NeMo guardrail configuration could not be loaded"
            ) from exc
        return self._rails

    def _normalize_result(
        self,
        request: GuardrailRequest,
        response: object,
        *,
        latency_ms: float,
    ) -> GuardrailResult:
        status = self._enum_value(getattr(response, "status", None))
        content = getattr(response, "content", None)
        rail = getattr(response, "rail", None)
        if status not in {"passed", "modified", "blocked"}:
            raise GuardrailExecutionError(self.name)
        if not isinstance(content, str):
            raise GuardrailExecutionError(self.name)
        if rail is not None and not isinstance(rail, str):
            raise GuardrailExecutionError(self.name)

        decision = {
            "passed": GuardrailDecision.ALLOW,
            "modified": GuardrailDecision.MODIFY,
            "blocked": GuardrailDecision.BLOCK,
        }[status]
        findings: tuple[GuardrailFinding, ...] = ()
        if decision is not GuardrailDecision.ALLOW:
            findings = (
                GuardrailFinding(
                    code=f"NEMO_RAIL_{status.upper()}",
                    name=f"NeMo rail {status}",
                    severity=GuardrailFindingSeverity.HIGH,
                    description=(
                        "The reviewed NeMo configuration changed or stopped content at "
                        "the selected guardrail stage."
                    ),
                    evidence_summary=(
                        f"NeMo reported {status}"
                        + (f" from rail '{rail}'." if rail else ".")
                    ),
                ),
            )

        return GuardrailResult(
            stage=request.stage,
            decision=decision,
            original_content=request.content,
            processed_content=(
                None if decision is GuardrailDecision.BLOCK else content
            ),
            triggered_rules=(rail,) if rail else (),
            findings=findings,
            adapter=self.name,
            latency_ms=latency_ms,
            metadata={
                "nemo_status": status,
                "llm_rail_configured": False,
            },
        )

    @staticmethod
    def _enum_value(value: Any) -> str:
        enum_value = getattr(value, "value", value)
        return enum_value if isinstance(enum_value, str) else ""
