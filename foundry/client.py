"""Small Azure AI Foundry client wrapper using passwordless Azure identity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import FoundryConfig, load_foundry_config


@dataclass
class FoundryClient:
    """Holds the project client and the configured support-agent identity.

    The wrapper deliberately does not create agents at import time; provisioning
    and runtime conversation logic will be implemented separately.
    """

    project_client: Any
    config: FoundryConfig


def create_foundry_client(config: FoundryConfig | None = None) -> FoundryClient:
    """Create an authenticated Foundry project client with Azure identity.

    ``DefaultAzureCredential`` uses a signed-in Azure CLI account locally and a
    managed identity or workload identity after deployment. It avoids storing an
    Azure key, token, or client secret in this repository.
    """

    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Azure SDK dependencies are unavailable. Install foundry/requirements.txt."
        ) from exc

    resolved_config = config or load_foundry_config()
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=resolved_config.project_endpoint,
        credential=credential,
    )
    return FoundryClient(project_client=project_client, config=resolved_config)
