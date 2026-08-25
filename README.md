# Pyromorphit

Pyromorphit is an agentified control surface for [Microsoft PyRIT](https://github.com/microsoft/PyRIT), rebuilt with the Palingen methodology.

It does **not** fork or rewrite PyRIT's mature attack, target, scorer, converter, scenario, or memory implementations. Instead it changes who owns orchestration:

- **PyRIT stays the deterministic security-testing capability layer.**
- **Pyromorphit Harness owns execution facts, evidence, permissions, checkpoints, and recovery.**
- **The host Agent owns semantic interpretation, strategy selection, adaptation, and composition.**
- **The human owns objectives, scope, and consequential authority, with intervention available without approval spam.**

The initial transformation is based on PyRIT `main` at `f9bcd1dd59dd9b5225fb9da8172faef3b84ceed9` (2026-08-24) and the Palingen skill in `ssweiplus/Palingen`.

## Why this shape

PyRIT already exposes strong execution primitives and, in current releases, a `pyrit_scan` CLI backed by the PyRIT backend. Pyromorphit treats that CLI/backend as an execution surface rather than duplicating its internals.

The result is **host-agent-native**: Pyromorphit does not require a second LLM endpoint just to orchestrate PyRIT. A capable host Agent can load the Pyromorphit Skill, invoke deterministic capabilities, inspect raw evidence, and decide the next action in the same attention surface used by the human.

```text
Human
  <-> one conversation / attention surface
  <-> Host Agent
        |-- Skill: PyRIT testing strategy and recovery heuristics
        |-- Harness: truth, evidence, limits, permissions, recovery
        `-- Tool: PyRIT CLI/backend
              `-- targets / scenarios / attacks / scorers / memory
```

## Status

This branch is the first coherent Agentification slice. It intentionally keeps large PyRIT regions coarse and focuses on transferring semantic control while preserving execution compatibility.

See:

- `docs/RESPONSIBILITY_MAP.md` — what stays, moves, and owns truth.
- `docs/ARCHITECTURE.md` — target form and migration slice.
- `docs/VALIDATION.md` — validation scope, evidence, and deferred environment checks.
- `skills/pyromorphit/SKILL.md` — reusable strategy for a host Agent.

## Install

Python 3.10–3.14 is supported by this slice, matching the current PyRIT range.

```bash
python -m pip install -e ".[pyrit]"
```

The `pyrit` extra is pinned to the upstream PyRIT commit used during this transformation so the first slice has a reproducible execution contract.

## Minimal execution surface

The CLI below is primarily for a host Agent, automation, debugging, and recovery. It is not intended to become another user-operated workflow engine.

Create a durable run:

```bash
pyromorphit --workspace .pyromorphit start \
  --objective "Assess the authorized target for prompt-injection weaknesses" \
  --max-concurrency 1
```

Use the returned `run_id` for deterministic PyRIT operations:

```bash
pyromorphit --workspace .pyromorphit exec --run-id <RUN_ID> -- \
  list-targets --start-server

pyromorphit --workspace .pyromorphit exec --run-id <RUN_ID> -- \
  run airt.cyber --target openai_chat --techniques single_turn --start-server
```

For `run`, Pyromorphit injects the run's concurrency ceiling when `--max-concurrency` is omitted. An explicit value above the Harness policy is rejected before process execution.

Inspect durable facts and evidence references:

```bash
pyromorphit --workspace .pyromorphit status --run-id <RUN_ID>
```

Record human action, correction, context, instruction, and authorization together when needed:

```bash
pyromorphit --workspace .pyromorphit note --run-id <RUN_ID> \
  --action-taken "logged in again" \
  --context "the old session cannot be resumed" \
  --correction "the token was valid; the server ended the session" \
  --instruction "continue from the current page"
```

Raw stdout/stderr artifacts are stored below `.pyromorphit/runs/<RUN_ID>/artifacts/`; `events.jsonl` keeps the append-only execution journal. Agent interpretation should reference these facts rather than replace them.

## Intended Agent surface

A user should be able to say things such as:

- "test this target for prompt-injection weaknesses"
- "only use single-turn techniques"
- "don't run concurrently"
- "show me why the last attempt failed"
- "change direction and reuse what already worked"
- "pause here; I need to log in again"

The user should **not** need to operate Palingen stages, choose internal tool IDs for routine work, or configure a separate orchestration-model API.

## Upstream

PyRIT is licensed under MIT. Pyromorphit is an independent transformation project and is not affiliated with or endorsed by Microsoft.
