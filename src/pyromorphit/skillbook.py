"""Packaged reusable strategy/knowledge, kept separate from execution truth."""

from importlib.resources import files


def load_red_team_strategy() -> str:
    """Load the default semantic red-team strategy shipped with Pyromorphit."""
    return files("pyromorphit").joinpath("skills/red_team_strategy.md").read_text(encoding="utf-8")
