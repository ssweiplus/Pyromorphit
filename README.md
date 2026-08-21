# Pyromorphit

**Pyromorphit is an agentified control layer for Microsoft PyRIT, derived with the Palingen methodology.**

It is deliberately **not a fork of PyRIT**. PyRIT already has strong deterministic capabilities — targets, attack strategies, converters, scorers, registries, memory, concurrency control, partial results, and resume-oriented attribution. Pyromorphit keeps those pieces intact and changes who owns semantic orchestration.

## Why

A fixed Scenario is useful when the playbook itself is the product. It becomes friction when the next useful action depends on what just happened, when the operator needs to intervene midway, or when a local failure should be repaired without discarding successful work.

Pyromorphit separates those responsibilities:

```text
Human
  ↕ goal / correction / authority
Agent
  ↕ semantic choice
Harness
  ↕ execution truth / evidence / recovery
PyRIT capabilities
  ↕
Targets / attacks / scorers / memory
```

- **Agent** decides which available capability to use next and when evidence is sufficient.
- **Harness** owns durable run state, raw evidence pointers, limits, pause/wait/recovery semantics.
- **PyRIT** owns deterministic attack execution, target contracts, scoring, native memory, retries and concurrency.
- **Skill** contains reusable red-team selection/recovery guidance without hiding a mandatory workflow.
- **Human** can correct or resume a run without becoming a retry/approval button for every step.

See [`docs/RESPONSIBILITY_MAP.md`](docs/RESPONSIBILITY_MAP.md) for the explicit Palingen responsibility allocation.

## What the first version does

1. Loads PyRIT's registered `AttackTechniqueFactory` objects.
2. Exposes each selected technique as an independently meaningful Agent capability.
3. Uses any PyRIT `PromptTarget` as the semantic planner, so Pyromorphit does not invent another LLM request contract.
4. Runs the chosen technique through PyRIT `AtomicAttack` / `AttackExecutor`.
5. Saves raw cross-capability evidence and an atomic `state.json` checkpoint under `.pyromorphit/runs/<run-id>/`.
6. Preserves completed work when a later capability raises an exception.
7. Supports `WAITING_FOR_HUMAN`, pause, correction, and resume.

PyRIT itself also continues to persist its native attack results in its configured memory backend.

## Installation

Python 3.10–3.14 is supported to match the current PyRIT line.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
```

The dependency is pinned to PyRIT commit `f10086d45b1301b6d591a3abb3f9a0d090b6fb6c` (the upstream `main` snapshot used for this transformation) so this first version is reproducible. Update that pin deliberately after compatibility testing.

## Minimal use

The complete example is in [`examples/minimal.py`](examples/minimal.py). The important integration path is:

```python
from pyromorphit.agent import PyromorphAgent
from pyromorphit.planner import PyRITTargetPlanner
from pyromorphit.pyrit_capabilities import build_registry_capabilities

capabilities = build_registry_capabilities(
    objective_target=objective_target,
    objective_scorer=objective_scorer,
    adversarial_chat=adversarial_chat,
    include_tags=["light"],
    max_concurrency=1,
)

agent = PyromorphAgent(
    planner=PyRITTargetPlanner(target=planner_target),
    capabilities=capabilities,
    max_steps=5,
)
state = await agent.run(goal="Assess the target against the authorized test objective.")
```

`max_concurrency=1` is intentional as a safe default for services that do not tolerate concurrent conversations. Raise it only when the target contract supports parallel execution.

## Human intervention

When the Agent reaches an authority/authentication/evidence boundary, it returns a durable run rather than hiding inside a blocking input call:

```python
if state.status.value == "waiting_for_human":
    print(state.pending_question)

state = await agent.resume(
    run_id=state.run_id,
    human_input="Correction or newly available context",
)
```

This makes a run usable from a chat UI, CLI, notebook, API, or another Agent harness without forcing any one UI contract into the core.

## Evidence layout

```text
.pyromorphit/runs/<run-id>/
├── state.json          # authoritative cross-capability checkpoint
├── events.jsonl        # append-only meaningful run events
└── evidence/
    └── 0001-<capability>-<sha>.json
```

The Agent sees compact summaries; raw evidence stays reachable. A local action failure is recorded as evidence and does not erase prior successful steps.

## Relationship to PyRIT Scenarios

Pyromorphit does not remove or replace Scenarios. Use a PyRIT Scenario when a repeatable fixed playbook is exactly what you want. Use Pyromorphit when technique choice, stopping, recovery, or human correction should be contextual.

The retained execution seam is:

```text
AttackTechniqueRegistry
  → AttackTechniqueFactory.create()
  → AtomicAttack.run_async()
  → AttackExecutor / PromptTarget / Scorers / Memory
```

That seam keeps the Agent at the semantic layer and avoids duplicating PyRIT internals.

## Status

This is the first transformation slice: capability exposure, semantic planning, execution truth, evidence persistence, and human resume. It intentionally does not yet add a dedicated UI, multi-agent coordination, or a replacement for PyRIT's native memory/analytics.
