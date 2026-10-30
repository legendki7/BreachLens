# Guardrails

Phase 6 implements a provider-independent defensive boundary with native deterministic
checks and an NVIDIA NeMo Guardrails adapter. Guardrails prevent, transform, or record
findings around content; they do not evaluate attack success or assign scores.

## Decision semantics

| Decision | Meaning for future orchestration |
| --- | --- |
| `allow` | Continue with unchanged content. |
| `block` | Stop; do not send input to the target or expose blocked output normally. |
| `modify` | Continue using `processed_content`. |
| `flag` | Continue while preserving structured findings. |
| `error` | Stop because content was not established as safe. |

Both input and output use the same normalized request, result, finding, and execution-
report contracts. Reports preserve each adapter's decision, triggered rules, findings,
latency, and timestamp. No guardrail evidence is persisted to `DuelTurn` yet.

## Phase 6 policy profiles

These behaviors are project-defined baselines, not production-ready security policies:

- `strict` enforces every adapter block.
- `moderate` enforces blocks only for critical findings with confidence of at least
  `0.8`; other blocks become flags.
- `permissive` observes blocks as flags except the explicit, critical, high-confidence
  native system-context-extraction condition.

Native checks are always enabled. NeMo runs only when explicitly enabled in runtime
policy configuration. Findings and existing flags are preserved under every profile.
The Phase 4 persisted profile configuration remains empty; Phase 6 resolves behavior
centrally at runtime rather than claiming production guardrails are already configured.

## Native deterministic checks

The native input rules detect narrow phrase patterns for requests to disclose system or
hidden instructions and explicit attempts to override earlier instructions. Input
matches produce raw block decisions for policy resolution.

The output rules flag protected-context labels and token-like formats. These are
heuristics only: they do not prove that context was disclosed, a token is real, or a
security breach occurred. The catalog is intentionally small and auditable rather than
presented as a complete jailbreak classifier.

## NVIDIA NeMo Guardrails

NVIDIA NeMo Guardrails is a third-party open-source defensive guardrail framework. It
was not developed by Red-Team Arena. The project uses the official base
`nemoguardrails` dependency on the `0.23.x` line, without optional provider/model
extras.

The reviewed configuration is in `apps/api/guardrails/nemo`. It defines one input and
one output rail backed by project-owned deterministic actions and configures no LLM.
NeMo is lazy-loaded only when requested, and its result types are normalized inside
`NeMoGuardrailAdapter`. It is never the target model and does not silently reuse target
or attacker models.

This integration demonstrates programmable input/output rails. It does not provide
complete OWASP coverage or configure retrieval, dialog, execution, or tool rails.

## Isolated development checks

The temporary `POST /api/v1/guardrails/test` endpoint performs one guardrail-stage
execution without calling the Red Agent or a target model. The equivalent local command
is:

```text
python -m scripts.test_guardrails --stage input --policy strict --content "..."
```

The command defaults to the native adapter. Add `--adapter nemo` explicitly to load the
reviewed NeMo configuration. Neither path accepts API credentials or performs target-
model generation.

`LLMGuardAdapter` is only a possible future or legacy integration point. LLM Guard is
not installed or implemented in Phase 6.
