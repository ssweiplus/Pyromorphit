# Pyromorphit Responsibility Map

Pyromorphit applies Palingen by changing ownership around PyRIT rather than rewriting PyRIT's deterministic internals.

| Responsibility | Before / PyRIT-centric path | Pyromorphit owner | Why |
| --- | --- | --- | --- |
| Decide which technique to try next | Scenario/playbook code, selector, or human notebook logic | Agent planner | This is contextual semantic composition. |
| Decide when evidence is sufficient | Scenario termination rules or human inspection | Agent planner, bounded by harness limits | Sufficiency depends on the assessment goal and accumulated evidence. |
| Execute an attack technique | PyRIT attack/executor stack | PyRIT capability | Deterministic execution contract should remain deterministic. |
| Validate target contracts / normalize messages | PyRIT `PromptTarget` | PyRIT | Stable execution I/O belongs below the semantic layer. |
| Score attack results | PyRIT scorers | PyRIT | Scoring output is evidence, not orchestration ownership. |
| Concurrency / partial execution | PyRIT `AttackExecutor` | PyRIT | Existing implementation already has controlled concurrency and partial results. |
| Raw per-step evidence | Ad hoc notebook/output + PyRIT memory | Harness + PyRIT memory | Harness records cross-capability truth; PyRIT retains its own native truth. |
| Run checkpoint / recovery | Scenario-specific resume or caller code | Harness | Cross-capability recovery must survive local failures and human pauses. |
| Reusable selection know-how | Scenario code / operator experience | Skill | Knowledge should guide decisions without hard-coding global sequencing. |
| Human correction / authority | Caller-specific | Human through Agent surface | Human can inspect, correct, pause, and resume without operating internal workflow states. |

## Boundary

```text
Human goal / correction
        ↓
PyromorphAgent               semantic decisions and composition
        ↓
ExecutionHarness             state, evidence, recovery, limits
        ↓
PyRITTechniqueCapability     stable semantic-to-execution adapter
        ↓
PyRIT Registry / AtomicAttack / AttackExecutor / PromptTarget / Scorers / Memory
```

The key rule is: **Agent asks; Harness mediates; PyRIT acts.**

PyRIT Scenarios remain usable. Pyromorphit is an additional control surface for cases where a fixed pre-packaged playbook is too rigid or where human notebook orchestration creates attention and recovery friction.
