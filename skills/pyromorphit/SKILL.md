# Pyromorphit Agent Skill

## Purpose

Use PyRIT as the deterministic AI-security implementation layer while the host Agent owns semantic testing strategy, interpretation, adaptation, and composition.

A core product constraint is:

> The human should not have to write Target/HTTP/Scenario access code merely to use PyRIT.

The human should be able to state goals, paste/describe an authorized interface, add constraints/corrections, and change direction in domain language.

## Responsibility boundaries

```text
Human
  owns objective, scope, consequential authority

Host Agent
  owns semantic choice, interpretation, composition, adaptation

Pyromorphit capabilities
  own stable access plumbing at useful boundaries:
  Catalog / HTTP Target / Target / Scenario / CLI escape hatch

Pyromorphit Harness
  owns execution facts, evidence, permissions, resource ceilings, recovery

PyRIT
  owns deterministic implementations:
  targets, scenarios, attacks, converters, scorers, memory, backend contracts
```

This Skill provides strategy and recovery knowledge. It does **not** own execution truth, authorization, concurrency ceilings, or PyRIT lifecycle invariants.

## Do not push access code onto the human

Before suggesting that the human write Python, a custom `PromptTarget`, `httpx` code, a Scenario constructor, or CLI assembly, check the promoted capability surface first.

Prefer:

```text
CatalogCapability        -> discover available component contracts
HTTPTargetCapability     -> raw HTTP request -> named PyRIT HTTPTarget
TargetCapability         -> create / restore / send
ScenarioCapability       -> describe / run / resume
PyRITCLI                 -> escape hatch only when no promoted capability fits
```

A stable execution contract belongs in deterministic capability code, not in repeated human-authored glue.

## HTTP target intake

For an ordinary HTTP endpoint without a dedicated PyRIT target, prefer PyRIT's native `HTTPTarget` through `HTTPTargetCapability`.

Ask the human only for information the Agent cannot infer safely, for example:

- an authorized raw request copied from Burp/devtools;
- where the model prompt belongs if it is not obvious;
- whether authentication must be refreshed manually;
- scope/side-effect constraints.

The normal input form is a raw request containing `{PROMPT}` at the model-input position. The human should not have to write request-send code or a `PromptTarget` subclass.

Target definitions can contain cookies/tokens and are sensitive run state. Do not print them into summaries or ordinary action metadata. Prefer environment placeholders or re-authentication when that is operationally appropriate.

## Capability discovery

Do not assume registry names or parameter contracts when PyRIT can describe them.

Use catalog discovery for:

- `target`
- `scenario`
- `converter`
- `scorer`

Use `describe` before inventing constructor parameters or forcing the human to look through source code.

## Operating posture

Prefer autonomous + reviewable execution.

Routine discovery, bounded target definition, bounded send, result inspection, and low-risk adaptation do not need repeated human approval when they remain inside the declared objective and Harness policy.

Block for the human only when authority, irreversibility, important evidence deficiency, or human-only capability requires it. Typical examples are re-authentication that should remain manual, a materially expanded target scope, or a high-impact operation that the Harness marks as requiring authorization.

Only test targets the human has authorized.

## Keep the objective stable

Treat the run objective and human constraints in the Harness as authoritative.

A technique's local goal, a scorer explanation, or a late-round hypothesis must not silently replace the original testing objective. When adapting strategy, re-anchor the proposed next action to the original objective and current human corrections.

## Strategy selection heuristics

Choose the least complicated capability that can produce meaningful evidence for the current objective.

Useful considerations include:

- whether the target is single-turn or multi-turn;
- whether a direct Target send is enough before a full Scenario;
- whether a baseline/direct attempt is valuable before transformations;
- whether a converter changes representation while preserving the intended semantic test;
- whether the target has rate/concurrency limitations;
- whether previous evidence shows refusal, transport failure, authentication failure, parsing failure, or genuine resistance;
- whether an intermediate result is independently useful enough to inspect, branch from, or hand to the human.

These are heuristics, not a mandatory numbered workflow.

## Target vs Scenario boundary

Use Target capabilities when the useful unit is direct interaction with one configured endpoint.

Use Scenario capabilities when PyRIT already owns a meaningful testing campaign/technique lifecycle.

Do not force a Scenario when one direct send answers the current question, and do not manually reproduce a Scenario's deterministic internals with a sequence of Target sends.

## Concurrency and resource behavior

Default concurrency is 1.

The Harness enforces the configured ceiling. Do not raise concurrency simply for speed when target session semantics, rate limits, or statefulness are uncertain.

`ScenarioCapability` injects the Harness concurrency ceiling rather than requiring the human to remember the matching PyRIT parameter.

## Evidence and interpretation

Raw execution evidence is authoritative for what actually happened. Agent interpretation is not.

When interpreting a result:

- distinguish process/transport success from security-objective success;
- distinguish PyRIT scorer/output facts from your own explanation;
- retain uncertainty when evidence is mixed;
- cite or point to the action/evidence that supports a conclusion;
- do not rewrite or normalize away raw evidence before it has been preserved.

The default human view should summarize meaningful status and evidence without dumping the entire trace. Raw evidence must remain reachable.

## Local failure and recovery

A failed action is not automatically a failed run.

Use preserved evidence and declarative target definitions to identify the smallest failed boundary. Prefer changing only that boundary rather than restarting everything.

Distinguish failures such as:

- target definition/parameter mismatch;
- backend unavailable;
- target transport error;
- authentication/session expiry;
- rate/concurrency issue;
- target capability mismatch;
- scenario/parameter mismatch;
- scorer/evaluation uncertainty;
- technique simply did not achieve the objective.

Do not blindly repeat an identical action when the evidence already explains why it failed.

## Contract friction

Treat stable transport, syntax, schema, and lifecycle mechanics as deterministic capability behavior whenever practical.

Examples:

```text
raw HTTP -> HTTPTarget             -> HTTP capability
Target constructor parameters      -> Target capability + catalog
PyRIT Message construction         -> Target capability
Scenario init parameters           -> Scenario capability + catalog
token/session factual state        -> Harness/Target fact
meaning of irregular output        -> Agent interpretation
choice of recovery strategy        -> Agent
human-only login/credential action -> Human
```

Use the lowest-cost resolution:

```text
remove -> standardize -> encode -> capability/lubricant
       -> Agent mediation -> Human escalation
```

Do not confuse "keep stable PyRIT implementation coarse" with "make the human call a coarse interface manually." Expose a smaller access capability when that removes repeated human glue.

## Human intervention

A human response may contain multiple things at once: an action they took, context, a correction, a new instruction, and/or authorization.

Record those together with the Harness rather than forcing one response type.

Useful natural controls include:

```text
查看当前情况
暂停
补充说明
改变方向
跳过这部分
从这里另开方案
继续
停止
```

Translate them into appropriate run facts/actions; do not expose internal enum/tool ceremony unnecessarily.

## Stop conditions

Stop or return to the human when:

- the objective is satisfied with enough evidence for the requested confidence;
- remaining adaptations are repeats with little new information;
- further work would expand scope or consequence beyond existing authority;
- a human-only action is required;
- evidence is too weak to justify a confident conclusion.

A partially successful run should be reported as such, with reusable evidence and the next viable options.
