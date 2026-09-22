"""Small, framework-independent service layer over the demo SQLite schema.

This module deliberately contains no UI or Azure/Foundry code.  Callers provide
validated user input to these methods and decide how to present their results.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Literal
from uuid import uuid4


Priority = Literal["low", "normal", "high", "urgent"]
SenderType = Literal["customer", "ai", "human", "system"]
_ORDER_NUMBER = re.compile(r"^CS-\d{4,}$", re.IGNORECASE)
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PRIORITIES = {"low", "normal", "high", "urgent"}
_SENDERS = {"customer", "ai", "human", "system"}


@dataclass(frozen=True)
class OrderDetails:
    """Customer-safe order information, never including address or payment data."""

    order_number: str
    status: str
    estimated_delivery_date: str | None
    delivered_at: str | None
    cancellation_eligible: bool
    return_eligible: bool
    items: tuple[dict[str, object], ...]
    events: tuple[dict[str, str | None], ...]


@dataclass(frozen=True)
class HandoffTicket:
    id: str
    conversation_id: str
    reason: str
    priority: str
    status: str
    ai_summary: str


class SupportService:
    """Transactional SQLite access for orders, conversations, and handoffs."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _order_number(order_number: str) -> str:
        normalized = order_number.strip().upper()
        if not _ORDER_NUMBER.fullmatch(normalized):
            raise ValueError("order_number must use the format CS- followed by at least four digits")
        return normalized

    @staticmethod
    def _nonempty(value: str, field: str, maximum: int = 8_000) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{field} cannot be empty")
        if len(cleaned) > maximum:
            raise ValueError(f"{field} cannot exceed {maximum} characters")
        return cleaned

    def lookup_order(self, order_number: str, customer_email: str | None = None) -> OrderDetails | None:
        """Find an order, optionally requiring its owning customer's email.

        A missing or mismatched order returns ``None`` so callers do not reveal
        whether a given order number belongs to another customer.
        """
        normalized_order = self._order_number(order_number)
        normalized_email = None
        if customer_email is not None:
            normalized_email = customer_email.strip().lower()
            if not _EMAIL.fullmatch(normalized_email):
                raise ValueError("customer_email must be a valid email address")

        with self._connect() as connection:
            row = connection.execute(
                """SELECT o.id, o.order_number, o.status, o.estimated_delivery_date,
                          o.delivered_at, o.cancellation_eligible, o.return_eligible
                   FROM orders o JOIN customers c ON c.id = o.customer_id
                   WHERE o.order_number = ? AND (? IS NULL OR lower(c.email) = ?)""",
                (normalized_order, normalized_email, normalized_email),
            ).fetchone()
            if row is None:
                return None
            items = connection.execute(
                """SELECT product_name, sku, quantity, unit_price_cents
                   FROM order_items WHERE order_id = ? ORDER BY product_name""", (row["id"],)
            ).fetchall()
            events = connection.execute(
                """SELECT event_type, event_at, location, details
                   FROM order_events WHERE order_id = ? ORDER BY event_at""", (row["id"],)
            ).fetchall()

        return OrderDetails(
            order_number=row["order_number"], status=row["status"],
            estimated_delivery_date=row["estimated_delivery_date"], delivered_at=row["delivered_at"],
            cancellation_eligible=bool(row["cancellation_eligible"]),
            return_eligible=bool(row["return_eligible"]),
            items=tuple(dict(item) for item in items), events=tuple(dict(event) for event in events),
        )

    def create_conversation(self, customer_id: str | None = None) -> str:
        """Create an active conversation, optionally connected to a known customer."""
        if customer_id is not None:
            customer_id = self._nonempty(customer_id, "customer_id", 128)
        conversation_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversations (id, customer_id) VALUES (?, ?)", (conversation_id, customer_id)
            )
        return conversation_id

    def add_message(self, conversation_id: str, sender_type: SenderType, body: str) -> str:
        """Persist one chat message and update the conversation activity timestamp."""
        conversation_id = self._nonempty(conversation_id, "conversation_id", 128)
        if sender_type not in _SENDERS:
            raise ValueError(f"sender_type must be one of: {', '.join(sorted(_SENDERS))}")
        body = self._nonempty(body, "body")
        message_id = str(uuid4())
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,)
            ).rowcount
            if not updated:
                raise LookupError("conversation does not exist")
            connection.execute(
                "INSERT INTO messages (id, conversation_id, sender_type, body) VALUES (?, ?, ?, ?)",
                (message_id, conversation_id, sender_type, body),
            )
        return message_id

    def list_messages(self, conversation_id: str) -> tuple[dict[str, str], ...]:
        """Return the persisted transcript, including replies from human support."""
        conversation_id = self._nonempty(conversation_id, "conversation_id", 128)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT sender_type, body, created_at FROM messages
                   WHERE conversation_id = ? ORDER BY created_at ASC, rowid ASC""",
                (conversation_id,),
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def get_handoff_for_conversation(self, conversation_id: str) -> HandoffTicket | None:
        """Return the handoff ticket for a conversation, if it has one."""
        conversation_id = self._nonempty(conversation_id, "conversation_id", 128)
        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, conversation_id, reason, priority, status, ai_summary
                   FROM handoff_tickets WHERE conversation_id = ?""",
                (conversation_id,),
            ).fetchone()
        return HandoffTicket(**dict(row)) if row is not None else None

    def create_handoff(self, conversation_id: str, reason: str, ai_summary: str, priority: Priority = "normal") -> HandoffTicket:
        """Queue a conversation for human support exactly once.

        The schema permits one ticket per conversation. Repeating this request
        returns the existing ticket, which prevents duplicate queue entries.
        """
        conversation_id = self._nonempty(conversation_id, "conversation_id", 128)
        reason = self._nonempty(reason, "reason", 500)
        ai_summary = self._nonempty(ai_summary, "ai_summary", 4_000)
        if priority not in _PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(sorted(_PRIORITIES))}")

        with self._connect() as connection:
            conversation = connection.execute(
                "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if conversation is None:
                raise LookupError("conversation does not exist")
            existing = connection.execute(
                "SELECT id, conversation_id, reason, priority, status, ai_summary FROM handoff_tickets WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if existing is None:
                ticket_id = str(uuid4())
                connection.execute(
                    """INSERT INTO handoff_tickets (id, conversation_id, reason, priority, ai_summary)
                       VALUES (?, ?, ?, ?, ?)""",
                    (ticket_id, conversation_id, reason, priority, ai_summary),
                )
                connection.execute(
                    "UPDATE conversations SET status = 'awaiting_human', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (conversation_id,),
                )
                connection.execute(
                    """INSERT INTO audit_events (id, conversation_id, event_type, actor_type, detail)
                       VALUES (?, ?, 'handoff_created', 'system', ?)""",
                    (str(uuid4()), conversation_id, f"priority={priority}; reason={reason}"),
                )
                existing = connection.execute(
                    "SELECT id, conversation_id, reason, priority, status, ai_summary FROM handoff_tickets WHERE id = ?",
                    (ticket_id,),
                ).fetchone()
        return HandoffTicket(**dict(existing))
