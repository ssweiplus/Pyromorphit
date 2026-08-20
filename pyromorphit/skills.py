from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    instructions: str
    strategies: list[dict]


class SkillLoader:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent.parent / "skills"

    def load(self, name: str) -> Skill:
        skill_dir = self.root / name
        skill_md = skill_dir / "SKILL.md"
        strategies_json = skill_dir / "strategies.json"
        if not skill_md.exists():
            raise FileNotFoundError(f"Skill not found: {name}")
        instructions = skill_md.read_text(encoding="utf-8")
        strategies = []
        if strategies_json.exists():
            strategies = json.loads(strategies_json.read_text(encoding="utf-8"))
        return Skill(name=name, instructions=instructions, strategies=strategies)
