# Pyromorphit

Pyromorphit is an **agent-first, human-in-the-loop red-team harness** for Agent security testing.

The project intentionally does **not** own the LLM control loop and does not require a fixed LLM API integration. It is designed to be opened by an agentic runtime such as Codex or OpenCode. The Agent is the semantic glue; Pyromorphit supplies skills, state, evidence, tools and invariants.

```text
Agent runtime (Codex / OpenCode / compatible agent)
        |
        v
     AGENTS.md
        |
        +--> Skills: testing knowledge and strategy
        +--> Harness: deterministic state/evidence operations
        +--> Human: execute prompts and return observations
        |
        v
Observe -> Reason -> Tool/Human action -> Observe -> Continue
```

## Core philosophy

- **Agent owns control flow**: no Python orchestrator calls an LLM to decide the next step.
- **Code provides capabilities, not workflows**: deterministic operations are exposed as small harness/tool capabilities.
- **Skills provide strategy, not hard-coded pipelines**: skills guide the Agent without forcing a fixed sequence.
- **Harness owns invariants**: immutable objectives, append-only evidence, session identity, turn relationships and audit history are not delegated to free-form model behavior.
- **Preserve raw before normalize**: target responses, operator notes and tool output are retained verbatim before interpretation.
- **Human is a first-class executor**: manual testing, new conversations, edits, retries and environment changes are explicit observations.
- **Everything important should be resumable**: the session archive is the durable source of truth, not chat history alone.

## Current scope

The first version focuses on the manual red-team loop:

```text
Skill + immutable objective
          |
          v
Agent chooses strategy and generates a test prompt
          |
          v
Human executes it against any target system
          |
          v
Human returns response + notes + actions
          |
          v
Agent evaluates evidence and chooses the next action
```

There is deliberately no Target abstraction, transport normalizer, automatic send/response loop, concurrency engine, or built-in LLM provider.

## Repository shape

```text
Pyromorphit/
├── AGENTS.md                  # Agent operating contract
├── skills/                    # Red-team knowledge and strategy
│   └── prompt_injection/
│       ├── SKILL.md
│       └── strategies.json
├── pyromorphit/               # Thin deterministic harness library
│   ├── models.py
│   ├── harness.py
│   ├── recorder.py
│   └── skills.py
├── docs/
│   └── AGENTIC_REFACTOR_PENDING.md
└── tests/
```

## Session archive

Each test session uses an append-oriented archive:

```text
test-report-{session-id}/
├── session.json
├── events.jsonl
├── tree.json
├── summary.md
└── turns/
    └── turn-001/
        ├── prompt.md
        ├── response.md
        ├── operator.json
        ├── evaluation.json
        └── analysis.md
```

The raw target response and human-provided information should never be overwritten by later summaries.

## Status

Pyromorphit is currently an experimental harness design. The broader methodology for converting conventional automation/workflow projects into agent-friendly harnesses is intentionally tracked as a pending design topic in `docs/AGENTIC_REFACTOR_PENDING.md`.
