# Architecture

## Migration boundary

Pyromorphit Agentifies the control plane around PyRIT. It does not replace PyRIT's execution engine.

### Before

```text
Human / script
  -> select/configure PyRIT workflow
  -> execute scenario/attack
  -> inspect result
  -> manually interpret
  -> manually choose retry/change/next technique
```

The semantic branch often lives in scripts, rigid orchestration, or the operator's head.

### After

```text
Human intent / correction
       |
       v
Host Agent  <---- strategy/recovery Skill
       |
       | proposes an action
       v
Pyromorphit Harness
  - validates scope and limits
  - records intent and execution fact boundary
  - invokes a deterministic capability
  - captures raw evidence and hashes
  - checkpoints durable progress
       |
       v
PyRIT execution surface
  - pyrit_scan / backend
  - scenarios / attacks / targets / scorers / memory
       |
       v
raw result/evidence
       |
       +----> Harness fact/evidence store
       |
       `----> Agent interprets and chooses what next
```

## First Agentification slice

The first complete slice is **run a PyRIT capability and return evidence without owning the next semantic decision**.

It contains:

1. Retained capability: current PyRIT CLI/backend operation.
2. Semantic boundary: Host Agent decides which safe capability to call and how to respond to results.
3. Truth boundary: Harness records command, timestamps, exit status, raw stdout/stderr artifact references and hashes.
4. Permission boundary: Harness applies explicit resource/verb policy.
5. Recovery boundary: each action is independently durable; later work can resume from prior evidence.
6. Human boundary: human can add context/correction, pause/change direction, or satisfy human-only authentication without being forced through routine approval prompts.

## State model

Three state layers are kept separate:

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

These are internal facts, not required user vocabulary. The user-facing message should say what was completed, what failed, what evidence survived, and what can happen next.

## Why use the PyRIT CLI/backend boundary first

Current PyRIT already provides `pyrit_scan` as a thin REST client for catalog discovery, scenario execution, history and results. Reusing this boundary:

- avoids duplicating Scenario/AttackExecutor behavior;
- keeps target/scorer/converter registries upstream;
- reduces version coupling to PyRIT internals;
- provides a naturally inspectable execution surface;
- lets the Agent reason over semantic output without owning transport mechanics.

Direct Python integration remains possible later for capabilities that genuinely need a finer boundary.

## Deferred by design

Not required for this first slice:

- a new graphical UI;
- another embedded orchestration LLM;
- a new PyRIT database;
- copying all PyRIT source into this repository;
- decomposing every attack into micro-tools;
- an MCP server (useful future connection surface, but not needed to prove responsibility transfer).
