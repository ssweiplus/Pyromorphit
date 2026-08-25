"""Deterministic adapter for PyRIT's current ``pyrit_scan`` execution surface."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from pyromorphit.model import ActionRequest, ExecutionResult


KNOWN_OPERATIONS = frozenset(
    {
        "run",
        "list-scenarios",
        "list-initializers",
        "list-targets",
        "list-converters",
        "scenario-results",
        "scenario-history",
        "start-server",
        "stop-server",
        "add-initializer",
    }
)


def _extract_operation(args: Sequence[str]) -> str:
    for token in args:
        if token in KNOWN_OPERATIONS:
            return token
    raise ValueError(
        "Could not find a supported pyrit_scan operation in arguments. "
        f"Known operations: {', '.join(sorted(KNOWN_OPERATIONS))}"
    )


def _flag_value(args: Sequence[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, token in enumerate(args):
        if token.startswith(prefix):
            return token[len(prefix) :]
        if token == flag:
            if index + 1 >= len(args):
                raise ValueError(f"Missing value for {flag}")
            return args[index + 1]
    return None


@dataclass(frozen=True)
class PyRITCLI:
    """A shell-free PyRIT CLI capability.

    The adapter owns transport/process details only. It does not decide which
    scenario, technique, target, or recovery strategy is semantically appropriate.
    """

    command: tuple[str, ...] = ("pyrit_scan",)
    cwd: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict)

    def prepare_request(
        self,
        *,
        args: Sequence[str],
        max_concurrency: int,
        human_authorized: bool = False,
    ) -> ActionRequest:
        if not args:
            raise ValueError("pyrit_scan arguments must not be empty")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        normalized = list(args)
        operation = _extract_operation(normalized)
        metadata: dict[str, object] = {}

        if operation == "run":
            raw_concurrency = _flag_value(normalized, "--max-concurrency")
            if raw_concurrency is None:
                normalized.extend(["--max-concurrency", str(max_concurrency)])
                requested_concurrency = max_concurrency
            else:
                try:
                    requested_concurrency = int(raw_concurrency)
                except ValueError as exc:
                    raise ValueError("--max-concurrency must be an integer") from exc
            metadata["max_concurrency"] = requested_concurrency

        return ActionRequest(
            capability="pyrit_scan",
            operation=operation,
            args=tuple(normalized),
            human_authorized=human_authorized,
            metadata=metadata,
        )

    def run(self, *, args: Sequence[str], timeout_s: float | None = None) -> ExecutionResult:
        command = (*self.command, *tuple(args))
        env = os.environ.copy()
        env.update(self.env)

        try:
            completed = subprocess.run(
                command,
                cwd=str(self.cwd) if self.cwd else None,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_s,
                check=False,
                shell=False,
            )
            return ExecutionResult(
                command=tuple(command),
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, bytes) else (exc.stdout or "").encode()
            stderr = exc.stderr if isinstance(exc.stderr, bytes) else (exc.stderr or "").encode()
            timeout_note = (
                f"\nPyromorphit timeout: command exceeded {timeout_s} seconds."
            ).encode("utf-8")
            return ExecutionResult(
                command=tuple(command),
                returncode=124,
                stdout=stdout,
                stderr=stderr + timeout_note,
            )
