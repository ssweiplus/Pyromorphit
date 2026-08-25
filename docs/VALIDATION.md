# Validation — capability-split Agentification slice

## Scope

This validation covers two responsibility transfers:

1. semantic next-step ownership moves to the host Agent;
2. stable access plumbing moves out of human-authored code into explicit Catalog / HTTP Target / Target / Scenario capabilities.

It does not claim live-target security effectiveness. Live target behavior belongs to the configured PyRIT target/scenario and must be validated only in an authorized environment.

## Checks

### Responsibility transfer

- PyRIT target/scenario/attack/scorer/converter **implementations** remain upstream.
- HTTP definition, Target create/restore/send, and Scenario describe/run/resume are promoted as independently meaningful access capabilities.
- The Host Agent is given strategy and interpretation guidance through `skills/pyromorphit/SKILL.md`, not a numbered workflow engine.
- Harness code contains permission/evidence/recovery mechanics but no attack-selection policy.
- `pyrit_scan` remains an escape hatch instead of being the only integration surface.

### No-code access boundary

- `CatalogCapability` exposes Target/Scenario/Converter/Scorer metadata so an Agent can discover parameters rather than invent them.
- `HTTPTargetCapability` accepts a raw HTTP request with `{PROMPT}` and builds PyRIT's native `HTTPTarget`.
- `TargetCapability` constructs PyRIT Message objects internally and invokes a named Target.
- `ScenarioCapability` binds a named Target and initializes/runs through PyRIT's `ScenarioRegistry`.
- Target definitions are persisted privately (`0600`) for cross-process recovery.
- Raw HTTP request text is not copied into normal Harness action metadata/journal events.

### Execution truth

- Objective and constraints are persisted independently of Agent narrative.
- Each invocation gets a durable action ID.
- Raw stdout and stderr/results are saved before interpretation and referenced by SHA-256.
- Reopening a run reconstructs completed action facts from the append-only journal.

### Partial failure

- A failed action is recorded as `FAILED_ACTION` with evidence.
- Previous successful artifacts and target definitions remain present and reusable.
- No automatic whole-run reset occurs.

### Permission and resource limits

- Unknown capabilities/operations are denied.
- `stop-server` and `add-initializer` require explicit human authorization.
- Default execution concurrency is 1.
- `ScenarioCapability` receives the Harness concurrency ceiling rather than trusting an unconstrained Agent value.

### Human intervention

- A single human note can contain an action taken, context, correction, instruction, and authorization together.
- The Skill tells the Agent to block only for real authority, irreversibility, evidence gaps, or human-only capability.

## Test evidence

The repository includes isolated tests under `tests/` for:

- Harness evidence/recovery/permissions;
- the legacy PyRIT CLI escape hatch;
- raw-HTTP target definition and private recovery;
- ensuring credential-bearing raw HTTP is not copied to the journal;
- Target send without user construction of PyRIT Message objects;
- Scenario binding of a named Target and the Harness concurrency ceiling.

`tests/test_capabilities.py` uses fake PyRIT registries/models, so these contract tests do not require a live target or a full PyRIT installation.

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the isolated suite on the PR branch. Live PyRIT compatibility remains a separate environment-level check.

## Deferred validation

The following require an environment with the relevant dependency and authority:

- installed `microsoft/PyRIT` at the pinned upstream commit;
- real `TargetRegistry` discovery across optional target dependencies;
- raw HTTP `HTTPTarget` smoke test against an authorized endpoint;
- live Scenario initialization/execution through the real `ScenarioRegistry`;
- target-specific login/session recovery;
- response extraction cases that need target-specific callbacks rather than raw response evidence;
- cryptographic binding of human authorization to an external identity system;
- MCP or another remote tool protocol.

## Outcome

The revised slice is suitable for review when its isolated test suite passes. The architecture now addresses the original human-friction goal more directly: stable access contracts are reusable capabilities, while semantic choices stay with the Agent and execution truth stays with Harness.
