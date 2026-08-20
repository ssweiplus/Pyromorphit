# Pyromorphit

Pyromorphit is a human-in-the-loop red-team reasoning framework for Agent security testing.

It deliberately does **not** send prompts to the target system. Instead, it helps a human tester iterate through:

```text
Skill -> Objective -> Strategy -> Prompt -> Human executes -> Feedback -> Score -> Analyze -> Next strategy
```

## Design principles

- **Objective is immutable**: the original test goal and success criteria are never rewritten by the LLM.
- **Human is an executor, not a transport**: responses, notes, prompt edits, new-session actions and environment changes are first-class evidence.
- **Every turn is auditable**: prompts, target responses, operator actions, evaluations and strategy decisions are appended to a session archive.
- **LLM as glue**: strategist, prompt-writer, judge and analyst are separate logical roles and can share one model provider.
- **No Target abstraction in v0**: no automatic send/receive, no concurrency, no protocol adapters.

## Quick start

Requires Python 3.11+.

```bash
python -m pyromorphit.cli --skill prompt_injection
```

By default the CLI uses a deterministic mock provider so the workflow can be explored without any API key.

Use an OpenAI-compatible endpoint:

```bash
export PYROMORPHIT_LLM_PROVIDER=openai-compatible
export PYROMORPHIT_LLM_BASE_URL=https://your-endpoint/v1
export PYROMORPHIT_LLM_API_KEY=...
export PYROMORPHIT_LLM_MODEL=...
python -m pyromorphit.cli --skill prompt_injection
```

## Session archive

Each run creates:

```text
test-report-{session-id}/
├── session.json
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

The archive is append-oriented and preserves the original human-provided content.

## Current scope

v0 focuses on the manual red-team loop. Automatic target adapters, parallel campaigns and transport normalization are intentionally out of scope for now.
