"""Self-contained verification for the service layer.

Run from the repository root: ``python services/verify.py``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.seed import seed  # noqa: E402
from services.support_service import SupportService  # noqa: E402


def verify() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "support-demo.db"
        seed(database_path)
        service = SupportService(database_path)

        order = service.lookup_order(" cs-1001 ", "alex.morgan@example.com")
        assert order is not None
        assert order.status == "shipped"
        assert order.items[0]["product_name"] == "Wireless Headphones"
        assert service.lookup_order("CS-1001", "jordan.lee@example.com") is None
        try:
            service.lookup_order("not-an-order")
            raise AssertionError("invalid order should fail validation")
        except ValueError:
            pass

        conversation_id = service.create_conversation("cust-alex")
        service.add_message(conversation_id, "customer", "My package has not arrived.")
        service.add_message(conversation_id, "ai", "I can see it is in transit.")
        ticket = service.create_handoff(
            conversation_id, "Customer requested a human", "Customer wants delivery assistance.", "high"
        )
        repeated_ticket = service.create_handoff(
            conversation_id, "ignored", "ignored", "normal"
        )
        assert ticket.id == repeated_ticket.id
        assert ticket.priority == "high"


if __name__ == "__main__":
    verify()
    print("Service layer verified.")
