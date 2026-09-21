"""Environment-based configuration for Azure AI Foundry.

No credentials are loaded from files. Authentication is delegated to
``DefaultAzureCredential`` in :mod:`foundry.client`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class FoundryConfigurationError(ValueError):
    """Raised when required Foundry configuration is absent or invalid."""


@dataclass(frozen=True)
class FoundryConfig:
    """Non-secret configuration required to use the support agent."""

    project_endpoint: str
    model_deployment_name: str
    agent_name: str
    agent_id: str | None = None


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise FoundryConfigurationError(
            f"Missing required environment variable: {name}. "
            "See foundry/README.md for local setup."
        )
    return value


def load_foundry_config() -> FoundryConfig:
    """Load non-secret Foundry settings from process environment variables."""

    endpoint = _required_environment("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint.startswith("https://"):
        raise FoundryConfigurationError(
            "FOUNDRY_PROJECT_ENDPOINT must be an HTTPS project endpoint."
        )

    agent_id = os.getenv("FOUNDRY_AGENT_ID", "").strip() or None
    return FoundryConfig(
        project_endpoint=endpoint.rstrip("/"),
        model_deployment_name=_required_environment("MODEL_DEPLOYMENT_NAME"),
        agent_name=_required_environment("FOUNDRY_AGENT_NAME"),
        agent_id=agent_id,
    )
