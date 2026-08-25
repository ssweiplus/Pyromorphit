# Responsibility Map

Source baseline: `microsoft/PyRIT@f9bcd1dd59dd9b5225fb9da8172faef3b84ceed9`.

## Suitability

Outcome: `LLM_WORKFLOW_AGENTIFICATION`.

PyRIT already participates in LLM red-team workflows and contains semantic decision points around attack selection, result interpretation, retry/adaptation, and campaign composition. Stable execution primitives are already mature, so the useful boundary is the **surrounding semantic orchestration**, not a rewrite of PyRIT.

## Living map

| Area | Responsibility atom | Current/retained capability | Proposed owner | Treatment |
|---|---|---|---|---|
| Objective and scope | Decision / Permission | caller input | Human + Harness | Preserve as immutable run facts unless human changes them |
| Choose scenario / technique | Decision | PyRIT catalogs + caller workflow | Agent | Move contextual choice to Agent |
| Build/run attack | Action | PyRIT Scenario / AttackExecutor / `pyrit_scan` | PyRIT Tool | Keep coarse and deterministic |
| Target protocol handling | Action | PyRIT PromptTarget and backend | PyRIT Tool | Keep deterministic; do not reimplement stable transport/schema |
| Target-specific unstable semantics | Decision | often encoded in glue or handled manually | Agent, supported by Skill | Interpret evidence above transport layer |
| Converters | Action / Knowledge | PyRIT converters | PyRIT Tool + Skill | Tool performs conversion; Agent chooses when/why |
| Scoring execution | Action | PyRIT scorers | PyRIT Tool | Keep |
| Meaning of mixed/ambiguous results | Decision | caller/orchestrator | Agent | Move to Agent; preserve raw score/result evidence |
| PyRIT memory | Truth for PyRIT internals | CentralMemory / result persistence | PyRIT | Preserve upstream contract |
| Cross-action run truth | Truth | scattered CLI output / caller state | Pyromorphit Harness | Add append-only facts/evidence and checkpoint references |
| Raw stdout/stderr/results | Truth / Artifact | CLI/backend output | Harness | Preserve before Agent interpretation |
| Retry/resource ceilings | Permission / Invariant | executor/config | Harness + PyRIT | Deterministic limits, not Agent prose |
| Concurrency | Permission / Invariant | AttackExecutor defaults to 1 | Harness | Default 1; only raise intentionally |
| Authentication/session lifecycle facts | Truth / Permission | target-specific | Tool/Harness/Human | Facts deterministic; recovery strategy Agent; human handles human-only auth |
| Routine continuation | Decision | fixed workflow / operator | Agent | Autonomous + reviewable |
| Consequential or human-only action | Permission | operator | Human | Blocking only where necessary |
| Strategy/recovery heuristics | Knowledge | docs/workflow code/operator knowledge | Skill | Extract knowledge, not numbered global workflow |
| Presentation | Narrative | CLI/UI output | Agent | Compress view, retain links to raw evidence |

## Contract friction treatment

| Layer | Examples in this transformation | Default treatment |
|---|---|---|
| Transport | CLI, REST backend, HTTP/SSE targets | PyRIT / deterministic adapters |
| Syntax / format | CLI flags, JSON/YAML, result text | deterministic code |
| Schema | target/scenario parameters | PyRIT registry/catalog |
| Lifecycle | backend startup, sessions, login/token expiry | Harness facts + deterministic capabilities; Agent chooses recovery |
| Semantic | whether a response achieved the objective; why a technique failed | Agent with raw evidence |
| Intent / social | test goal, changed direction, human annotations | Human <-> Agent |

## Invariants

Even if Agent reasoning is wrong:

1. The declared objective/scope and human constraints remain recoverable facts.
2. Raw execution evidence is retained before interpretation.
3. An action failure does not erase prior successful evidence.
4. Resource/concurrency/permission ceilings are enforced deterministically.
5. Agent narrative cannot overwrite execution facts.
6. Human-only authorization remains human-owned.
7. Upstream PyRIT artifacts and memory contracts are not silently rewritten.

## Intentionally left coarse

The following remain upstream capabilities in this slice:

- attack implementations;
- scenarios and scenario techniques;
- prompt targets;
- converters;
- scorers;
- PyRIT memory/database internals;
- backend catalog and result APIs.

They can be revisited only when a concrete semantic-control, recovery, human-intervention, or compatibility benefit justifies finer decomposition.
