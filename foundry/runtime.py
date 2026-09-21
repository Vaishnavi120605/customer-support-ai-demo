"""Runtime invocation of the deployed Microsoft Foundry support agent.

The HTTP call intentionally uses :class:`DefaultAzureCredential` instead of an
API key.  It works with ``az login`` during local development and with a managed
identity in an Azure deployment.
"""

from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import FoundryConfig, load_foundry_config


class FoundryInvocationError(RuntimeError):
    """Raised when the support agent cannot return a usable response."""


def _access_token() -> str:
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise FoundryInvocationError(
            "Azure identity dependencies are unavailable. Install requirements.txt."
        ) from exc
    return DefaultAzureCredential().get_token("https://ai.azure.com/.default").token


def _extract_text(payload: dict[str, Any]) -> str:
    """Extract the text output from an OpenResponses-compatible payload."""
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise FoundryInvocationError("The agent returned no customer-visible text.")


def ask_support_agent(message: str, config: FoundryConfig | None = None) -> str:
    """Send one grounded customer message to the configured prompt agent."""
    customer_message = message.strip()
    if not customer_message:
        raise ValueError("message cannot be empty")
    resolved = config or load_foundry_config()
    url = (
        f"{resolved.project_endpoint}/agents/{resolved.agent_name}"
        "/endpoint/protocols/openai/responses?api-version=v1"
    )
    body = json.dumps(
        {"input": [{"role": "user", "content": customer_message}]}
    ).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        # certifi avoids a common macOS Python installation issue where the
        # standard library has no configured CA bundle. It still verifies TLS.
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=45, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise FoundryInvocationError(f"Foundry request failed with HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise FoundryInvocationError("Could not reach the Foundry support agent.") from exc
    return _extract_text(payload)
