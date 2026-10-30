# Reviewed NeMo configuration

This Phase 6 configuration demonstrates explicit input and output rail integration
using two small project-owned deterministic actions. It does not configure an LLM,
reuse the target model, reuse the attacker model, or require provider credentials.

The input rail checks narrow explicit system-context extraction and instruction-
override phrases. The output rail checks narrow protected-context labels and token-like
formats. These heuristics are not a classifier, do not prove a breach, and do not claim
complete OWASP or AI-safety coverage.

The configuration is loaded lazily only when the `nemo` adapter is explicitly enabled.
The independently implemented native adapter remains the default offline baseline.
