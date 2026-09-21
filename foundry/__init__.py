"""Azure AI Foundry integration primitives for the support-chat application."""

from .client import FoundryClient, create_foundry_client
from .config import FoundryConfig, load_foundry_config

__all__ = [
    "FoundryClient",
    "FoundryConfig",
    "create_foundry_client",
    "load_foundry_config",
]
