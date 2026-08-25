# Pyromorphit

Pyromorphit is an agentified control surface for [Microsoft PyRIT](https://github.com/microsoft/PyRIT), rebuilt with the Palingen methodology.

It keeps PyRIT's mature implementations, but **does not require the human to write access/orchestration code just to use them**.

- **PyRIT** stays the deterministic security-testing implementation layer.
- **Pyromorphit capabilities** expose Catalog / HTTP Target / Target / Scenario as Agent-callable units.
- **Pyromorphit Harness** owns execution facts, evidence, permissions, checkpoints, and recovery.
- **The host Agent** owns semantic interpretation, strategy selection, adaptation, and composition.
- **The human** owns objectives, scope, and consequential authority.

The transformation is based on PyRIT `main` at `f9bcd1dd59dd9b5225fb9da8172faef3b84ceed9` (2026-08-24) and the Palingen skill in `ssweiplus/Palingen`.

## Target form

```text
Human
  <-> one conversation / attention surface
  <-> Host Agent
        |-- Skill
        |-- Catalog capability
        |-- HTTP Target capability
        |-- Target capability
        |-- Scenario capability
        |-- Harness: truth / evidence / permission / recovery
        `-- PyRIT implementations
              |-- HTTPTarget / other PromptTargets
              |-- TargetRegistry / ScenarioRegistry
              `-- attacks / converters / scorers / memory
```

The split is deliberate: PyRIT internals can stay coarse while the **access boundary is fine enough to remove human-authored glue**.

## Install

```bash
python -m pip install -e ".[pyrit]"
```

## Agent-facing capability surface

The CLI is primarily for a host Agent, automation, debugging, and recovery. A human should normally stay in the conversation and provide intent/evidence, not operate these commands manually.

Create a durable run:

```bash
pyromorphit --workspace .pyromorphit start \
  --objective "Assess the authorized target for prompt-injection weaknesses" \
  --max-concurrency 1
```

### Discover contracts instead of reading source/writing constructors

```bash
pyromorphit catalog --kind target
pyromorphit catalog --kind target --name HTTPTarget
pyromorphit catalog --kind scenario
pyromorphit catalog --kind scenario --name airt.cyber
pyromorphit catalog --kind converter
pyromorphit catalog --kind scorer
```

### HTTP target: paste a raw request, do not write a PromptTarget

Put `{PROMPT}` where the model input belongs. For example `request.txt` may contain:

```http
POST /api/chat HTTP/1.1
Host: internal.example
Content-Type: application/json
Cookie: session=...

{"message":"{PROMPT}"}
```

Define it as a reusable run-local PyRIT `HTTPTarget`:

```bash
pyromorphit --workspace .pyromorphit define-http \
  --run-id <RUN_ID> \
  --name internal-chat \
  --request-file request.txt
```

No `httpx` code, `PromptTarget` subclass, PyRIT `Message` construction, or initializer script is required for this ordinary raw-HTTP case.

The target definition is stored under the run in a private `0600` file so it can be restored in a later process. Raw requests may contain credentials; treat `.pyromorphit/` as sensitive local state.

### Direct Target interaction

```bash
pyromorphit --workspace .pyromorphit send \
  --run-id <RUN_ID> \
  --target internal-chat \
  --prompt "hello"
```

`TargetCapability` reconstructs the target if necessary, builds the PyRIT `Message`, invokes `send_prompt_async`, and puts the raw result behind Harness evidence references.

### Scenario execution

```bash
pyromorphit --workspace .pyromorphit run-scenario \
  --run-id <RUN_ID> \
  --scenario airt.cyber \
  --target internal-chat \
  --technique single_turn
```

The Scenario capability binds the named Target, initializes via PyRIT's `ScenarioRegistry`, injects the Harness concurrency ceiling, runs the Scenario, and captures the raw result. The Agent decides which Scenario/technique is appropriate; the human does not assemble the Python objects.

### Escape hatch

`exec` remains available for PyRIT operations not yet promoted to a first-class capability:

```bash
pyromorphit --workspace .pyromorphit exec --run-id <RUN_ID> -- \
  scenario-history 20 --start-server
```

It is no longer the intended primary integration surface.

## Recovery and human intervention

Inspect durable facts and evidence references:

```bash
pyromorphit --workspace .pyromorphit status --run-id <RUN_ID>
```

Record human action, correction, context, instruction, and authorization together:

```bash
pyromorphit --workspace .pyromorphit note --run-id <RUN_ID> \
  --action-taken "logged in again" \
  --context "the old session cannot be resumed" \
  --correction "the token was valid; the server ended the session" \
  --instruction "continue from the current page"
```

A failed Target send or Scenario does not erase earlier successful evidence or target definitions.

## Intended human surface

A user should be able to say things such as:

- "这是 Burp 里抓到的请求，消息字段在这里，帮我接进去"
- "先直接发一条看看返回结构"
- "再选择合适的 PyRIT scenario 测试"
- "只用单轮技术，不要并发"
- "上个 session 失效了，我已经重新登录，继续"
- "这个结果别用了，从前一个成功结果换个方向"

The user should **not** need to write target access code, operate Palingen stages, choose internal tool IDs for routine work, or configure a second orchestration-model API.

## Design notes

See:

- `docs/RESPONSIBILITY_MAP.md` — what stays, moves, and owns truth.
- `docs/ARCHITECTURE.md` — why access boundaries are split while PyRIT internals remain reused.
- `docs/VALIDATION.md` — validation scope and deferred environment checks.
- `skills/pyromorphit/SKILL.md` — reusable strategy for a host Agent.

## Upstream

PyRIT is licensed under MIT. Pyromorphit is an independent transformation project and is not affiliated with or endorsed by Microsoft.
