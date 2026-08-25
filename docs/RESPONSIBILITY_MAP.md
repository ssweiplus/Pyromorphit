# Responsibility Map

Source baseline: `microsoft/PyRIT@f9bcd1dd59dd9b5225fb9da8172faef3b84ceed9`.

## Suitability

Outcome: `LLM_WORKFLOW_AGENTIFICATION`.

PyRIT already participates in LLM red-team workflows and contains semantic decision points around attack selection, result interpretation, retry/adaptation, and campaign composition. It also exposes stable execution primitives whose construction/access contracts should be hidden from the human when possible.

The useful boundary is therefore:

- preserve PyRIT's mature implementations;
- expose HTTP/Target/Scenario/etc. as independently meaningful capabilities;
- move semantic composition to the Agent;
- keep truth/permission/recovery in Harness.

## Living map

| Area | Responsibility atom | Current/retained capability | Proposed owner | Treatment |
|---|---|---|---|---|
| Objective and scope | Decision / Permission | caller input | Human + Harness | Preserve as immutable run facts unless human changes them |
| Choose scenario / technique | Decision | PyRIT catalogs + caller workflow | Agent | Move contextual choice to Agent |
| Discover component contracts | Knowledge / Action | PyRIT registries | Catalog capability | Expose Target/Scenario/Converter/Scorer metadata directly |
| Raw HTTP integration | Action | PyRIT `HTTPTarget` | HTTP Target capability | Human supplies raw request/template; capability builds target; no custom access code |
| Target construction | Action | `TargetRegistry.create_instance` | Target capability | Build from declarative parameters and register by name |
| Target restore | Action / Truth | target definition + registry | Target capability + Harness workspace | Rehydrate run-local target without rewriting adapter code |
| Target send | Action | `PromptTarget.send_prompt_async` | Target capability | Capability constructs PyRIT Message and captures raw response |
| Target-specific unstable semantics | Decision | often encoded in glue or handled manually | Agent, supported by Skill | Interpret evidence above transport layer |
| Scenario construction | Action | `ScenarioRegistry.create_and_initialize_async` | Scenario capability | Bind target/params/techniques without user Python |
| Scenario execution/resume | Action | PyRIT Scenario | Scenario capability | Keep scenario internals upstream; expose run/resume boundary |
| Attack internals | Action | PyRIT Scenario / AttackExecutor | PyRIT | Keep coarse unless finer intervention creates demonstrated value |
| Converters | Action / Knowledge | PyRIT converters | PyRIT + Catalog/Skill | Discover contract; Tool performs conversion; Agent chooses when/why |
| Scoring execution | Action | PyRIT scorers | PyRIT + Catalog | Keep deterministic; expose contract rather than requiring constructor code |
| Meaning of mixed/ambiguous results | Decision | caller/orchestrator | Agent | Move to Agent; preserve raw score/result evidence |
| PyRIT memory | Truth for PyRIT internals | CentralMemory / result persistence | PyRIT | Preserve upstream contract |
| Cross-action run truth | Truth | scattered CLI output / caller state | Pyromorphit Harness | Append-only facts/evidence and checkpoint references |
| Raw stdout/stderr/results | Truth / Artifact | capability output | Harness | Preserve before Agent interpretation |
| Target definitions | Recovery / Access contract | previously caller code | Target capability + run workspace | Private run-local declarative definitions; may contain secrets |
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
| Transport | HTTP/SSE/WebSocket/CLI | deterministic capability using existing PyRIT Target |
| Syntax / format | raw HTTP, JSON/YAML, result text | deterministic capability; user should not write parser/client code for stable forms |
| Schema | Target/Scenario parameters | catalog introspection + declarative data |
| Lifecycle | target restore, backend startup, sessions, login/token expiry | Harness facts + deterministic capabilities; Agent chooses recovery |
| Semantic | whether a response achieved the objective; why a technique failed | Agent with raw evidence |
| Intent / social | test goal, changed direction, human annotations | Human <-> Agent |

## Important correction to the coarse-first rule

"Prefer the largest safe unit of reuse" does **not** mean "expose the largest possible API to the user."

For Pyromorphit:

```text
keep implementation coarse
+ expose access boundary at useful capability granularity
```

Example:

```text
HTTPTarget internals stay intact
but
HTTP definition / Target send / Scenario run are separate Agent-callable capabilities
```

This removes user-authored glue without needlessly forking PyRIT.

## Invariants

Even if Agent reasoning is wrong:

1. The declared objective/scope and human constraints remain recoverable facts.
2. Raw execution evidence is retained before interpretation.
3. An action failure does not erase prior successful evidence.
4. Resource/concurrency/permission ceilings are enforced deterministically.
5. Agent narrative cannot overwrite execution facts.
6. Human-only authorization remains human-owned.
7. Upstream PyRIT artifacts and memory contracts are not silently rewritten.
8. Stable transport/access mechanics are not pushed back onto the human as code-writing work.

## Intentionally left coarse

The following remain upstream **implementations**, even though their access boundaries may be promoted as Pyromorphit capabilities:

- attack implementations;
- scenario implementations and scenario techniques;
- prompt-target implementations;
- converters;
- scorers;
- PyRIT memory/database internals;
- backend internals.

Further decomposition should be justified by semantic control, recovery, human intervention, or removal of additional user-authored glue.
