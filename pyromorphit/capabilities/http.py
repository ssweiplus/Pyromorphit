"""No-code HTTP target definition using PyRIT's native HTTPTarget."""

from __future__ import annotations

from typing import Any

from pyromorphit.capabilities.target import TargetCapability, TargetHandle


class HTTPTargetCapability:
    """Turn a raw Burp/cURL-style HTTP request template into a reusable PyRIT target."""

    def __init__(self, targets: TargetCapability) -> None:
        self.targets = targets

    def define(
        self,
        *,
        name: str,
        raw_request: str,
        prompt_marker: str = "{PROMPT}",
        use_tls: bool = True,
        follow_redirects: bool = True,
        max_requests_per_minute: int | None = None,
        model_name: str = "",
        persist_definition: bool = True,
        human_authorized: bool = False,
        **httpx_client_kwargs: Any,
    ) -> TargetHandle:
        """Define an HTTP target by data only; no PromptTarget subclass is required."""
        if not raw_request.strip():
            raise ValueError("raw_request must not be empty")
        if prompt_marker not in raw_request:
            raise ValueError(
                f"raw_request must contain the prompt marker {prompt_marker!r}; "
                "place it where the model input belongs"
            )
        parameters: dict[str, Any] = {
            "http_request": raw_request,
            "prompt_regex_string": prompt_marker,
            "use_tls": use_tls,
            "follow_redirects": follow_redirects,
            "model_name": model_name,
        }
        if max_requests_per_minute is not None:
            parameters["max_requests_per_minute"] = max_requests_per_minute
        parameters.update(httpx_client_kwargs)
        return self.targets.create(
            name=name,
            type_name="HTTPTarget",
            parameters=parameters,
            persist_definition=persist_definition,
            human_authorized=human_authorized,
        )
