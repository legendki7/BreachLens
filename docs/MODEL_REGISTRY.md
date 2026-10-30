# Model Registry

Phase 2 implements relational target-model identity, Phase 3 adds provider-independent execution with a Hugging Face adapter, Phase 5 adds a transient attacker-model contract, and Phase 7 adds a transient Judge Model contract. No registry data is seeded, and models are called only through explicit API or developer-script requests.

## ModelProvider

`ModelProvider` identifies the access mechanism or provider family for one or more target models. It stores:

- UUID identifier
- name and globally unique slug
- provider type
- optional base URL
- active state
- creation and update timestamps

A provider is retained while any target model references it through a restrictive foreign key.

## TargetModel

`TargetModel` identifies a model available through one provider. It stores:

- UUID identifier and provider relationship
- display name
- canonical model identifier
- optional description and model family
- flexible non-secret JSONB configuration
- third-party status
- active state
- creation and update timestamps

The pair `(provider_id, canonical_model_id)` is unique. This allows different providers to expose similarly named models while preventing duplicate canonical identifiers inside one provider.

Target models referenced by historical duels cannot be deleted through a cascading relationship. Set `is_active` to false when a model should no longer be selectable.

## Hugging Face integration

Hugging Face is an implemented execution platform and routing layer, represented by a `ModelProvider` whose `provider_type` is `huggingface`. The adapter uses the target's canonical model identifier with `huggingface_hub.InferenceClient.chat_completion`.

`TargetModel.configuration` may contain non-secret generation defaults such as `temperature` and `max_tokens`, plus an optional `provider_route`. If no route is supplied, the adapter uses Hugging Face's `auto` routing behavior. Credentials are not valid model configuration.

The Hugging Face platform/provider and the external model are distinct third parties. Integrating the platform does not imply ownership, authorship, endorsement, or availability of any model hosted or routed through it.

## Model roles

Model role and provider are separate concepts:

- A **target model** is the subject being security-tested. Registered target models are persisted in `TargetModel` and will be selected by future duel orchestration.
- An **attacker model** generates one controlled test prompt for the Red Agent. Phase 5 accepts an explicit runtime configuration with canonical model ID, provider, third-party status, and role `attacker`; it creates a transient gateway-compatible model and does not persist it as a target or assume both roles use the same model.
- A **judge model** applies a versioned scenario rubric to supplied interaction evidence. Phase 7 uses a transient runtime contract with canonical model ID, provider, third-party status, explicit role `judge`, independent generation settings, and non-secret provider configuration. It is not persisted or silently reused from attacker/target roles.

Attacker and Judge Models both execute through `ModelGateway` but use independent
runtime identities and generation settings. Red Agent generation does not inherit
target settings; Judge defaults are temperature `0.0` and maximum output `800` tokens.
External attacker or Judge Models are third-party dependencies, not models developed
by the Red-Team Arena project.

## Security boundary

Provider API keys, tokens, passwords, and other credentials must never be stored in either registry table or in model configuration JSON. `HF_TOKEN` is loaded from application environment configuration and is never included in normalized responses. The gateway rejects stored configuration containing credential-like keys.

## Experiment disclosure requirements

Every model selected for later hackathon experiments must record:

- canonical model identifier
- model creator or organization, when known
- execution provider
- purpose
- project role
- third-party status

No external model may be presented as owned by the Red-Team Arena project.

Third-party models used as targets, attackers, or judges must be identified by
role and disclosed in the hackathon Team Statement.

Phase 7 automated tests mock Judge execution. No real external Judge Model has been
used or represented as project-developed.
