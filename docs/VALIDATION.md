# Validation — first Agentification slice

## Scope

This validation covers the first Pyromorphit control slice: deterministic PyRIT capability invocation through a Harness while semantic next-step ownership remains with the host Agent.

It does not claim live-target security effectiveness. Live target behavior belongs to the configured PyRIT target/scenario and must be validated in the environment where it is authorized to run.

## Checks

### Responsibility transfer

- PyRIT target/scenario/attack/scorer/converter implementations remain outside Pyromorphit.
- The Host Agent is given strategy and interpretation guidance through `skills/pyromorphit/SKILL.md`, not a numbered workflow engine.
- Harness code contains permission/evidence/recovery mechanics but no attack-selection policy.

### Execution truth

- Objective and constraints are persisted independently of Agent narrative.
- Each invocation gets a durable action ID.
- Raw stdout and stderr are saved before interpretation and referenced by SHA-256.
- Reopening a run reconstructs completed action facts from the append-only journal.

### Partial failure

- A failed action is recorded as `FAILED_ACTION` with evidence.
- Previous successful artifacts remain present and reusable.
- No automatic whole-run reset occurs.

### Permission and resource limits

- Unknown capabilities/operations are denied.
- `stop-server` and `add-initializer` require an explicit human-authorization fact.
- Default execution concurrency is 1, and the Harness rejects a higher requested concurrency when the run policy does not allow it.

### Human intervention

- A single human note can contain an action taken, context, correction, instruction, and authorization together.
- The Skill tells the Agent to block only for real authority, irreversibility, evidence gaps, or human-only capability.

## Test evidence

The repository includes isolated unit tests for the Harness and PyRIT CLI adapter under `tests/`. They do not need a live PyRIT backend or target.

A local smoke check of the same code path used a fake command in place of `pyrit_scan` and verified:

- concurrency `1` was injected into a `run` invocation;
- the command executed without a shell;
- raw stdout was persisted as an evidence artifact;
- the successful action remained recoverable as `PARTIALLY_COMPLETE`.

## Deferred validation

The following are intentionally deferred until an environment supplies the relevant dependency or authority:

- smoke test against an installed `microsoft/PyRIT` at the pinned upstream commit;
- live backend startup/catalog discovery;
- authorized live target scenario execution;
- target-specific login/session recovery;
- cryptographic binding of a human authorization fact to an external identity system;
- MCP or another remote tool protocol.

## Outcome

The first slice is accepted for review with deferred environment-specific validation. The intended control transfer is present without rewriting PyRIT's mature deterministic implementation, while the remaining validation items are boundary-specific rather than reasons to restart the transformation.
