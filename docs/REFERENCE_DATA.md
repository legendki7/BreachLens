# Reference Data

Red-Team Arena keeps external security references separate from its operational
assessment taxonomy. Canonical definitions live in `apps/api/app/reference_data` and
are persisted only when the explicit reference-data seeder is run.

## External Reference Data

### OWASP GenAI LLM Top 10 2026

- Framework: OWASP GenAI LLM Top 10
- Version: 2026
- Release date: 2026-08-03
- Official source: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/

The risk identifiers and names below are attributed to the OWASP GenAI Security
Project. The descriptions stored by Red-Team Arena are concise, original project
summaries rather than copied OWASP text.

| Code | OWASP risk name |
| --- | --- |
| LLM01:2026 | Prompt Injection |
| LLM02:2026 | Sensitive Information Disclosure |
| LLM03:2026 | Excessive Agency |
| LLM04:2026 | Supply Chain |
| LLM05:2026 | Data and Model Poisoning |
| LLM06:2026 | Unbounded Consumption |
| LLM07:2026 | Misinformation |
| LLM08:2026 | Hidden Context Exposure |
| LLM09:2026 | Vector and Embedding Weaknesses |
| LLM10:2026 | Improper Output Handling |

## Red-Team Arena Defined Data

The scenarios, attack patterns, policy profiles, and their operational mappings are
Red-Team Arena design choices. They are not presented as official OWASP terminology
or normative OWASP mappings.

### Scenarios and OWASP mappings

| Scenario | Severity | Explicit OWASP mapping |
| --- | --- | --- |
| Jailbreak | critical | LLM01:2026 Prompt Injection |
| Direct Prompt Injection | critical | LLM01:2026 Prompt Injection |
| Indirect Prompt Injection | critical | LLM01:2026 Prompt Injection |
| Sensitive Information Disclosure | critical | LLM02:2026 Sensitive Information Disclosure |
| Hidden Context Exposure | high | LLM08:2026 Hidden Context Exposure |
| Misinformation | high | LLM07:2026 Misinformation |
| Toxicity | high | None |
| Self-Harm | critical | None |
| Model / Policy Specification Violation | high | None |

Jailbreaking is modeled as a prompt-injection scenario, not as a separate OWASP risk.
The three broader AI-safety scenarios intentionally have no OWASP mapping: not every
AI-safety failure is automatically an OWASP LLM Top 10 vulnerability.

### Red-Team Arena attack taxonomy

The initial reusable attack patterns are:

- Role Play Framing (`role_play_framing`)
- Authority Impersonation (`authority_impersonation`)
- Hypothetical Framing (`hypothetical_framing`)
- Instruction Override (`instruction_override`)
- Many-Shot Priming (`many_shot_priming`)
- Multi-Turn Escalation (`multi_turn_escalation`)
- Indirect Injection (`indirect_injection`)
- Obfuscation (`obfuscation`)
- Encoded Payload (`encoded_payload`)
- Multilingual Bypass (`multilingual_bypass`)
- Context Extraction (`context_extraction`)
- Social Engineering Framing (`social_engineering_framing`)

Initial scenario-to-pattern mappings are project configuration:

- Jailbreak: role play framing, authority impersonation, hypothetical framing,
  instruction override, many-shot priming, multi-turn escalation, obfuscation,
  encoded payload, and multilingual bypass.
- Direct Prompt Injection: instruction override, authority impersonation, obfuscation,
  encoded payload, and multilingual bypass.
- Indirect Prompt Injection: indirect injection, obfuscation, and encoded payload.
- Hidden Context Exposure: context extraction, authority impersonation, social
  engineering framing, and multi-turn escalation.

### Policy profiles

The built-in profiles are ordered from most to least strict: `strict`, `moderate`, and
`permissive`. Their persisted configuration is empty in Phase 4. The records describe
future defensive postures; they do not claim that any guardrail is active.

## Explicit seeding

After the PostgreSQL schema is migrated, seed or reconcile the catalog from
`apps/api`:

```text
python -m scripts.seed_reference_data
```

The command runs in a single transaction. It updates canonical scalar values by
stable natural keys and creates missing relationships, so rerunning it does not create
duplicates. It is never invoked during FastAPI startup. No model, provider, or
credential records are included.
