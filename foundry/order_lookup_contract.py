"""Typed, provider-neutral contract for the SQLite order lookup tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class OrderLookupRequest:
    """Validated input passed from an agent tool call to the data layer."""

    order_number: str
    customer_email: str | None = None


@dataclass(frozen=True)
class OrderLookupResult:
    """Safe order fields that may be returned to the customer-support agent."""

    found: bool
    order_number: str
    status: Literal[
        "pending",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
        "returned",
        "unknown",
    ]
    estimated_delivery_date: str | None = None
    tracking_number: str | None = None
    carrier: str | None = None
    eligible_for_cancellation: bool | None = None
    message: str | None = None


class OrderLookupTool(Protocol):
    """Interface the eventual SQLite implementation must satisfy."""

    def lookup(self, request: OrderLookupRequest) -> OrderLookupResult:
        """Return verified, customer-safe order data without exposing PII."""
