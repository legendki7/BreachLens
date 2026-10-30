from pydantic import ValidationError

from app.evaluation.contracts import JudgeStructuredOutput
from app.evaluation.exceptions import JudgeOutputValidationError


class JudgeOutputParser:
    """Validate exact JSON with one isolated Markdown-fence compatibility path."""

    def parse(self, content: str) -> JudgeStructuredOutput:
        candidate = self._remove_json_fence(content.strip())
        try:
            return JudgeStructuredOutput.model_validate_json(candidate)
        except ValidationError as exc:
            raise JudgeOutputValidationError() from exc

    @staticmethod
    def _remove_json_fence(content: str) -> str:
        if not content.startswith("```"):
            return content
        lines = content.splitlines()
        if (
            len(lines) < 3
            or lines[0].strip().casefold() not in {"```", "```json"}
            or lines[-1].strip() != "```"
        ):
            raise JudgeOutputValidationError()
        return "\n".join(lines[1:-1]).strip()
