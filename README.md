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
- `skills/pyromorphit/SKILL.md` — reusable strategy for a host Agent.

## Planned user surface

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
