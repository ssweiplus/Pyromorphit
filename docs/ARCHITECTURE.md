# Architecture

## Migration boundary

Pyromorphit Agentifies the control plane around PyRIT. It does not replace PyRIT's execution engine, but it **does expose PyRIT at capability boundaries fine enough that the human does not have to write access/orchestration code**.

### Before

```text
Human / script
  -> write/configure target access code
  -> construct PyRIT Target/Scenario objects or CLI flags
  -> execute scenario/attack
  -> inspect result
  -> manually interpret
  -> manually choose retry/change/next technique
```

Two different burdens are mixed here:

1. semantic orchestration — deciding what to test and what a result means;
2. execution-contract plumbing — HTTP requests, Target construction, Scenario parameters, registry names, Message objects, CLI flags.

The human should own neither burden when it can be handled safely by Agent + deterministic capability code.

### After

```text
Human intent / raw request / correction
       |
       v
Host Agent  <---- strategy/recovery Skill
       |
       | semantic composition
       v
Pyromorphit capability surface
  +-- Catalog       discover contracts
  +-- HTTP Target   raw request -> reusable Target
  +-- Target        create / restore / send
  +-- Scenario      describe / run / resume
  +-- CLI escape hatch for capabilities not promoted yet
       |
       v
Pyromorphit Harness
  - validates scope and limits
  - records execution facts
  - captures raw evidence and hashes
  - preserves durable progress
       |
       v
PyRIT implementations
  - HTTPTarget / PromptTarget
  - TargetRegistry / ScenarioRegistry
  - scenarios / attacks / converters / scorers / memory
       |
       v
raw result/evidence
       |
       +----> Harness fact/evidence store
       |
       `----> Agent interprets and chooses what next
```

## Capability decomposition rule

Palingen's coarse-first rule applies to **implementation internals**, not to forcing the user to operate a coarse API.

Keep PyRIT's mature internals coarse, but expose independently meaningful access capabilities when doing so removes user-authored glue:

```text
PyRIT HTTPTarget implementation     -> retained coarse implementation
HTTP target definition              -> exposed capability
Target Registry implementation      -> retained coarse implementation
Target create/restore/send           -> exposed capability
Scenario implementation             -> retained coarse implementation
Scenario describe/run/resume         -> exposed capability
Attack internals                     -> retained unless a finer intervention point has demonstrated value
```

This distinction is important: **we split the access boundary, not necessarily the underlying implementation**.

## No-code HTTP target path

For HTTP-style internal applications, the intended path is:

```text
Human/Agent supplies raw HTTP request
          |
          | put {PROMPT} where model input belongs
          v
HTTPTargetCapability.define(...)
          |
          v
PyRIT HTTPTarget
```

The human does not write a `PromptTarget` subclass, `httpx` client, Message construction code, or response-transport adapter for the ordinary raw-request case.

Target definitions are stored under the run as private `0600` JSON so a later process can reconstruct the PyRIT Target. Since raw HTTP requests can contain credentials, the run workspace must be treated as sensitive local state.

## Target capability

`TargetCapability` owns deterministic access plumbing:

- discover Target types and constructor contracts;
- create a Target from data;
- register it by a stable run-local name;
- restore it from the saved definition;
- construct PyRIT `Message` objects internally;
- invoke `send_prompt_async` and return raw evidence through Harness.

It does **not** decide which target is semantically appropriate or what the response means.

## Scenario capability

`ScenarioCapability` owns deterministic Scenario plumbing:

- discover Scenario names, techniques, datasets, and declared parameters;
- bind a named Target;
- inject the Harness concurrency ceiling;
- initialize through PyRIT's `ScenarioRegistry`;
- run or resume a scenario;
- return the raw PyRIT result as Harness evidence.

The Agent chooses which Scenario/techniques to use based on the human objective and prior evidence.

## State model

Three state layers remain separate:

- **Fact state**: immutable/append-only execution facts owned by Harness.
- **Working state**: Agent hypotheses, interpretations, candidate next actions.
- **Narrative state**: concise explanation shown to the human.

Only fact state is authoritative for what actually ran and what it returned.

## Failure model

An action can fail without making the entire run unusable.

```text
RUNNING
PARTIALLY_COMPLETE
WAITING_FOR_HUMAN
BLOCKED
FAILED_ACTION
COMPLETED
```

Target definition, a successful earlier send, or a prior Scenario result remains usable when a later action fails.

## CLI role

`pyrit_scan` remains supported, but it is now an **escape hatch**, not the primary Agent surface.

The promoted path is capability-specific:

```text
catalog
  -> define-http / Target create
  -> send
  -> run-scenario
```

These commands are still primarily for the host Agent, automation, debugging, and recovery. They should not become a human-operated wizard.

## Deferred by design

Not required for this slice:

- a new graphical UI;
- another embedded orchestration LLM;
- a new PyRIT database;
- copying all PyRIT source into this repository;
- decomposing every attack into micro-tools;
- forcing every target protocol into HTTP when PyRIT already has a native Target;
- an MCP server (a useful future connection surface once the capability contracts settle).
