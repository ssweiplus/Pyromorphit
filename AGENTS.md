# Agent instructions

When using this repository to operate PyRIT, load `skills/pyromorphit/SKILL.md`.

Pyromorphit is host-agent-native: do not introduce another orchestration LLM unless the user explicitly asks for one. The host Agent owns semantic composition; Pyromorphit Harness owns execution truth and constraints; PyRIT performs deterministic security-testing capabilities.

Do not bypass the Harness for executions that belong to an active Pyromorphit run, because raw evidence, permission checks, partial failure, and recovery would be lost.
