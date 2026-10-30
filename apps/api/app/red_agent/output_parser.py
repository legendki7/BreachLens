from pydantic import ValidationError

from app.red_agent.contracts import GeneratedAttackOutput
from app.red_agent.exceptions import RedAgentOutputValidationError


class RedAgentOutputParser:
    """Validate exact JSON, with one isolated Markdown-fence compatibility path."""

    def parse(self, content: str) -> GeneratedAttackOutput:
        candidate = self._remove_json_fence(content.strip())
        try:
            return GeneratedAttackOutput.model_validate_json(candidate)
        except ValidationError as exc:
            raise RedAgentOutputValidationError() from exc

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
            raise RedAgentOutputValidationError()
        return "\n".join(lines[1:-1]).strip()
