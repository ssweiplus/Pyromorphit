from __future__ import annotations

import json
import stat
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

from pyromorphit.capabilities.catalog import CatalogCapability
from pyromorphit.session import PyromorphitSession


class FakeInstances:
    def __init__(self) -> None:
        self.items: dict[str, object] = {}

    def register(self, instance: object, *, name: str, metadata=None) -> None:
        self.items[name] = instance

    def get(self, name: str):
        return self.items.get(name)


@dataclass
class FakeMetadata:
    registry_name: str
    class_name: str
    parameters: tuple[str, ...] = ()


class FakeTarget:
    def __init__(self, **parameters) -> None:
        self.parameters = parameters

    def get_identifier(self):
        return {"type": "FakeTarget"}

    async def send_prompt_async(self, *, message):
        return [{"echo": message.message_pieces[0].original_value}]


class FakeTargetRegistry:
    def __init__(self) -> None:
        self.instances = FakeInstances()

    def get_all_registered_class_metadata(self):
        return [FakeMetadata(registry_name="HTTPTarget", class_name="HTTPTarget", parameters=("http_request",))]

    def get_registered_class_metadata(self, name: str):
        if name == "HTTPTarget":
            return FakeMetadata(registry_name=name, class_name=name, parameters=("http_request",))
        return None

    def get_class_names(self):
        return ["HTTPTarget"]

    def create_instance(self, name: str, **parameters):
        assert name == "HTTPTarget"
        return FakeTarget(**parameters)


class FakeScenario:
    async def run_async(self):
        return {"outcome": "completed", "source": "fake-scenario"}


class FakeScenarioRegistry:
    def get_all_registered_class_metadata(self):
        return [FakeMetadata(registry_name="demo.scenario", class_name="DemoScenario")]

    def get_registered_class_metadata(self, name: str):
        if name == "demo.scenario":
            return FakeMetadata(registry_name=name, class_name="DemoScenario")
        return None

    def get_class_names(self):
        return ["demo.scenario"]

    async def create_and_initialize_async(self, name: str, **kwargs):
        assert name == "demo.scenario"
        assert kwargs["max_concurrency"] == 1
        assert kwargs["objective_target"] is not None
        return FakeScenario()


@pytest.fixture
def fake_pyrit_models(monkeypatch):
    pyrit_module = types.ModuleType("pyrit")
    models_module = types.ModuleType("pyrit.models")

    class MessagePiece:
        def __init__(self, *, role, original_value, original_value_data_type):
            self.role = role
            self.original_value = original_value
            self.original_value_data_type = original_value_data_type

    class Message:
        def __init__(self, *, message_pieces):
            self.message_pieces = message_pieces

    models_module.Message = Message
    models_module.MessagePiece = MessagePiece
    pyrit_module.models = models_module
    monkeypatch.setitem(sys.modules, "pyrit", pyrit_module)
    monkeypatch.setitem(sys.modules, "pyrit.models", models_module)


def test_http_definition_is_data_only_private_and_recoverable(tmp_path: Path, monkeypatch):
    target_registry = FakeTargetRegistry()
    scenario_registry = FakeScenarioRegistry()

    def registry(kind: str):
        return target_registry if kind == "target" else scenario_registry

    monkeypatch.setattr(CatalogCapability, "_registry", staticmethod(registry))
    session = PyromorphitSession.create(workspace=tmp_path, objective="authorized test")

    raw = "POST /chat HTTP/1.1\nHost: example.test\nCookie: secret\n\n{\"message\":\"{PROMPT}\"}"
    handle = session.http.define(name="internal-chat", raw_request=raw)
    assert handle.name == "internal-chat"

    definition = session.harness.run_dir / "definitions" / "targets" / "internal-chat.json"
    assert definition.exists()
    assert stat.S_IMODE(definition.stat().st_mode) == 0o600
    saved = json.loads(definition.read_text(encoding="utf-8"))
    assert saved["type_name"] == "HTTPTarget"
    assert saved["parameters"]["http_request"] == raw

    # Raw request/credential material is not copied into normal Harness request metadata.
    event_text = session.harness.journal_path.read_text(encoding="utf-8")
    assert "Cookie: secret" not in event_text

    # Simulate a later process where the in-memory Target registry has been lost.
    target_registry.instances.items.clear()
    restored = session.targets.get("internal-chat")
    assert isinstance(restored, FakeTarget)


def test_target_send_hides_pyrit_message_construction(tmp_path: Path, monkeypatch, fake_pyrit_models):
    target_registry = FakeTargetRegistry()
    scenario_registry = FakeScenarioRegistry()
    monkeypatch.setattr(
        CatalogCapability,
        "_registry",
        staticmethod(lambda kind: target_registry if kind == "target" else scenario_registry),
    )
    session = PyromorphitSession.create(workspace=tmp_path, objective="authorized test")
    session.http.define(
        name="internal-chat",
        raw_request="POST /chat HTTP/1.1\nHost: example.test\n\n{\"message\":\"{PROMPT}\"}",
    )

    record = session.targets.send(name="internal-chat", prompt="hello")
    assert record.succeeded
    evidence = session.harness.run_dir / record.stdout.path
    assert "hello" in evidence.read_text(encoding="utf-8")


def test_scenario_binds_named_target_and_harness_concurrency(tmp_path: Path, monkeypatch):
    target_registry = FakeTargetRegistry()
    scenario_registry = FakeScenarioRegistry()
    monkeypatch.setattr(
        CatalogCapability,
        "_registry",
        staticmethod(lambda kind: target_registry if kind == "target" else scenario_registry),
    )
    session = PyromorphitSession.create(workspace=tmp_path, objective="authorized test", max_concurrency=1)
    session.http.define(
        name="internal-chat",
        raw_request="POST /chat HTTP/1.1\nHost: example.test\n\n{\"message\":\"{PROMPT}\"}",
    )

    record = session.scenarios.run(
        name="demo.scenario",
        target="internal-chat",
        techniques=["single_turn"],
    )
    assert record.succeeded
    evidence = session.harness.run_dir / record.stdout.path
    assert "fake-scenario" in evidence.read_text(encoding="utf-8")
