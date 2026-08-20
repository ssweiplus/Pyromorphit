# Pending: General Agentic Refactor Methodology

This document intentionally records a design topic rather than a finished specification.

## Goal

Develop a reusable method for transforming conventional automation/workflow codebases into agent-friendly harnesses.

The central inversion is:

```text
Traditional:
Code -> call LLM -> parse -> branch -> call system -> parse -> continue

Agentic harness:
Agent -> inspect state/skills -> call capability -> observe raw result -> adapt -> continue
                         ^
                      Harness
```

## Working principles

1. Code provides capabilities, not end-to-end workflows.
2. The Agent owns semantic glue and adaptive control flow.
3. Skills provide domain strategy and operating knowledge.
4. The Harness owns invariants, state, events, artifacts and resumability.
5. Preserve raw evidence before semantic normalization.
6. Normalize transport envelopes where useful; avoid target-specific semantic normalization unless deterministic structure provides clear value.
7. Treat humans as first-class executors/tools when operations cannot or should not be automated.
8. Prefer event-sourced, append-oriented state for auditability, branching and replay.
9. Permit temporary Agent-generated glue in a sandbox; promote repeated stable glue into reusable deterministic tools.
10. Keep the Agent runtime replaceable: Codex, OpenCode or another compatible agent should be able to operate the same harness.

## Questions to research

- How to identify workflow code that should become tools versus invariants versus skills?
- What is the minimal universal ToolResult envelope without recreating semantic normalizers?
- How should state be partitioned into immutable facts, working hypotheses, events and artifacts?
- What state mutations may an Agent propose, and what must the Harness enforce?
- How should temporary Agent-generated glue be sandboxed, audited and promoted into reusable tools?
- What compatibility layer is needed across different agent runtimes and skill conventions?
- How should checkpoints and resume semantics work when humans or external systems pause execution?
- What objective metrics can compare a conventional workflow implementation with its agentic-harness refactor?
- Where should deterministic code remain preferable to LLM interpretation?
- How can existing codebases be mechanically analyzed and classified into workflow, capability, parser, policy, state and presentation components?

## Desired output later

Turn this into a reusable refactoring playbook, tentatively:

```text
Discover -> Classify -> Cut -> Expose -> Constrain -> Skillify -> Persist -> Validate
```

The methodology should be broader than Pyromorphit and applicable to existing automation, integration, testing and operational tooling projects.
