"""Lazy, code-free discovery of PyRIT component contracts."""

from __future__ import annotations

import dataclasses
from enum import Enum
from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Convert PyRIT metadata/results to durable JSON-friendly values."""
    if dataclasses.is_dataclass(value):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return to_jsonable(model_dump(mode="json"))
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_jsonable(to_dict())
    return repr(value)


class CatalogCapability:
    """Discover Target/Scenario/Converter/Scorer contracts without user code."""

    _REGISTRIES = {
        "target": "TargetRegistry",
        "scenario": "ScenarioRegistry",
        "converter": "ConverterRegistry",
        "scorer": "ScorerRegistry",
    }

    @staticmethod
    def _registry(kind: str) -> Any:
        registry_name = CatalogCapability._REGISTRIES.get(kind)
        if registry_name is None:
            raise ValueError(f"Unsupported component kind: {kind}")
        try:
            import pyrit.registry as registry_module
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise RuntimeError("PyRIT is not installed; install Pyromorphit with the 'pyrit' extra") from exc
        registry_cls = getattr(registry_module, registry_name)
        return registry_cls.get_registry_singleton()

    def list_types(self, kind: str) -> list[dict[str, Any]]:
        registry = self._registry(kind)
        return [to_jsonable(item) for item in registry.get_all_registered_class_metadata()]

    def describe(self, kind: str, name: str) -> dict[str, Any]:
        registry = self._registry(kind)
        metadata = registry.get_registered_class_metadata(name)
        if metadata is None:
            available = ", ".join(registry.get_class_names())
            raise KeyError(f"Unknown {kind} {name!r}. Available: {available}")
        return to_jsonable(metadata)
