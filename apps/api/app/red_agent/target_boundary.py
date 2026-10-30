import re

_PROTECTED_CLAUSE = re.compile(
    r"\b(?:never|do\s+not|must\s+not|should\s+not)\s+"
    r"(?:reveal|disclose|expose|share|provide|output|print)\s+([^.;]+)",
    re.IGNORECASE,
)
_EXTRACTION_INTENT = re.compile(
    r"\b(?:"
    r"(?:explanation|description|disclosure|reproduction)s?\s+of|"
    r"provid(?:e|es|ed|ing)(?:\s+me)?(?:\s+with)?|"
    r"reveal(?:s|ed|ing)?|"
    r"show(?:s|ed|ing)?(?:\s+me)?|"
    r"tell(?:s|ing)?\s+me|"
    r"give(?:s|n|ing)?\s+me|"
    r"disclos(?:e|es|ed|ing)|"
    r"explain(?:s|ed|ing)?|"
    r"walk(?:s|ed|ing)?\s+me\s+through|"
    r"reproduc(?:e|es|ed|ing)|"
    r"output(?:s|ted|ting)?|"
    r"print(?:s|ed|ing)?"
    r")\b",
    re.IGNORECASE,
)
_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_CONCEPT_SPLIT = re.compile(r",|\bor\b", re.IGNORECASE)
_LEADING_FILLER = frozenset({"a", "an", "and", "any", "the"})


class TargetBoundaryMatcher:
    """Match explicit extraction attempts against concepts protected by this target."""

    def protected_concept_labels(
        self,
        target_security_boundary: str | None,
    ) -> tuple[str, ...]:
        """Return concise normalized labels for prompts and diagnostics."""
        return tuple(
            " ".join(concept)
            for concept in self.protected_concepts(target_security_boundary)
        )

    def attempts_protected_extraction(
        self,
        attack_prompt: str,
        target_security_boundary: str | None,
    ) -> bool:
        concepts = self.protected_concepts(target_security_boundary)
        if not concepts:
            return False

        for intent in _EXTRACTION_INTENT.finditer(attack_prompt):
            requested_tokens = self._normalize_tokens(attack_prompt[intent.end() :])
            if any(
                self._contains_concept(requested_tokens, concept)
                for concept in concepts
            ):
                return True
        return False

    def protected_concepts(
        self,
        target_security_boundary: str | None,
    ) -> tuple[tuple[str, ...], ...]:
        if not target_security_boundary:
            return ()

        concepts: list[tuple[str, ...]] = []
        for clause in _PROTECTED_CLAUSE.findall(target_security_boundary):
            for phrase in _CONCEPT_SPLIT.split(clause):
                tokens = list(self._normalize_tokens(phrase))
                while tokens and tokens[0] in _LEADING_FILLER:
                    tokens.pop(0)
                if len(tokens) >= 2:
                    concept = tuple(tokens)
                    if concept not in concepts:
                        concepts.append(concept)
        return tuple(concepts)

    @classmethod
    def _normalize_tokens(cls, text: str) -> tuple[str, ...]:
        return tuple(cls._singularize(token.casefold()) for token in _TOKEN.findall(text))

    @staticmethod
    def _singularize(token: str) -> str:
        if len(token) > 4 and token.endswith("ies"):
            return f"{token[:-3]}y"
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            return token[:-1]
        return token

    @classmethod
    def _contains_concept(
        cls,
        requested_tokens: tuple[str, ...],
        concept: tuple[str, ...],
    ) -> bool:
        variants = [concept]
        if len(concept) >= 3:
            variants.append(concept[1:])
        return any(
            len(variant) >= 2
            and cls._contains_ordered_tokens(requested_tokens, variant)
            for variant in variants
        )

    @staticmethod
    def _contains_ordered_tokens(
        requested_tokens: tuple[str, ...],
        concept: tuple[str, ...],
    ) -> bool:
        for start, token in enumerate(requested_tokens):
            if token != concept[0]:
                continue
            position = start
            matched = True
            for expected in concept[1:]:
                next_position = next(
                    (
                        index
                        for index in range(position + 1, min(position + 4, len(requested_tokens)))
                        if requested_tokens[index] == expected
                    ),
                    None,
                )
                if next_position is None:
                    matched = False
                    break
                position = next_position
            if matched:
                return True
        return False
