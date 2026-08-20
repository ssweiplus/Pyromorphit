from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass
class MockProvider:
    """Deterministic provider for exploring the workflow without an API."""

    def complete(self, system: str, user: str) -> str:
        if "JUDGE_ROLE" in system:
            return json.dumps({
                "result": "PARTIAL",
                "score": 0.4,
                "confidence": 0.5,
                "achieved": [],
                "not_achieved": ["Objective not demonstrably achieved"],
                "defenses_observed": [],
                "weaknesses_observed": [],
                "rationale": "Mock evaluation; configure an LLM provider for semantic judging."
            })
        if "ANALYST_ROLE" in system:
            return "Mock analysis: preserve the original objective and vary one strategy dimension next turn."
        if "PROMPT_WRITER_ROLE" in system:
            return "[MOCK TEST PROMPT] Replace this with an LLM-generated prompt after configuring a provider."
        return json.dumps({
            "family": "baseline",
            "tactic": "direct_probe",
            "rationale": "Establish a baseline before mutation.",
            "preserve": [],
            "change": [],
            "avoid": []
        })


@dataclass
class OpenAICompatibleProvider:
    base_url: str
    api_key: str
    model: str

    def complete(self, system: str, user: str) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def provider_from_env() -> LLMProvider:
    provider = os.getenv("PYROMORPHIT_LLM_PROVIDER", "mock")
    if provider == "mock":
        return MockProvider()
    if provider == "openai-compatible":
        return OpenAICompatibleProvider(
            base_url=os.environ["PYROMORPHIT_LLM_BASE_URL"],
            api_key=os.environ.get("PYROMORPHIT_LLM_API_KEY", ""),
            model=os.environ["PYROMORPHIT_LLM_MODEL"],
        )
    raise ValueError(f"Unsupported provider: {provider}")
