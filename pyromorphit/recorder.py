from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from .models import TestSession, Turn


def _json_default(value):
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def _dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=_json_default)


class SessionRecorder:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.cwd()

    def session_dir(self, session: TestSession) -> Path:
        path = self.root / f"test-report-{session.id}"
        path.mkdir(parents=True, exist_ok=True)
        (path / "turns").mkdir(exist_ok=True)
        return path

    def save_session(self, session: TestSession) -> None:
        base = self.session_dir(session)
        (base / "session.json").write_text(_dump(session.to_dict()), encoding="utf-8")
        tree = {
            "session_id": session.id,
            "nodes": [
                {
                    "turn_id": t.id,
                    "parent_turn_id": t.parent_turn_id,
                    "strategy": t.strategy.family,
                    "tactic": t.strategy.tactic,
                    "result": t.evaluation.result if t.evaluation else None,
                    "score": t.evaluation.score if t.evaluation else None,
                }
                for t in session.turns
            ],
        }
        (base / "tree.json").write_text(_dump(tree), encoding="utf-8")
        self._write_summary(session, base)

    def append_event(self, event: dict, session: TestSession) -> None:
        base = self.session_dir(session)
        with (base / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=_json_default) + "\n")

    def save_turn(self, session: TestSession, turn: Turn) -> None:
        base = self.session_dir(session) / "turns" / f"turn-{turn.id:03d}"
        base.mkdir(parents=True, exist_ok=True)
        (base / "prompt.md").write_text(turn.prompt, encoding="utf-8")
        if turn.feedback:
            (base / "response.md").write_text(turn.feedback.target_response, encoding="utf-8")
            (base / "operator.json").write_text(_dump(turn.feedback), encoding="utf-8")
        if turn.evaluation:
            (base / "evaluation.json").write_text(_dump(turn.evaluation), encoding="utf-8")
        if turn.analysis:
            (base / "analysis.md").write_text(turn.analysis, encoding="utf-8")
        self.save_session(session)

    def _write_summary(self, session: TestSession, base: Path) -> None:
        lines = [
            f"# Test Session {session.id}",
            "",
            f"- Skill: {session.skill_name}",
            f"- State: {session.state}",
            f"- Objective: {session.objective.description}",
            "",
            "## Turns",
        ]
        for turn in session.turns:
            result = turn.evaluation.result if turn.evaluation else "PENDING"
            lines.append(f"- Turn {turn.id}: {turn.strategy.family}/{turn.strategy.tactic} -> {result}")
        (base / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
