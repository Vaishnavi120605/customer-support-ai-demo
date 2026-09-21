"""Create a deterministic SQLite database for local demos and tests.

Run: python database/seed.py [path/to/customer_support.db]
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


DATABASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
DEFAULT_DATABASE_PATH = DATABASE_DIR / "customer_support_demo.db"


CUSTOMERS = [
    ("cust-alex", "Alex Morgan", "alex.morgan@example.com"),
    ("cust-jordan", "Jordan Lee", "jordan.lee@example.com"),
    ("cust-sam", "Sam Rivera", "sam.rivera@example.com"),
]

ORDERS = [
    ("order-1001", "CS-1001", "cust-alex", "shipped", "paid", 8999, 0, "USD", "12 Market Street, Seattle, WA 98101", "2026-09-18T10:15:00Z", "2026-09-24", None, 0, 1, None),
    ("order-1002", "CS-1002", "cust-jordan", "processing", "paid", 4500, 599, "USD", "48 Lake Avenue, Austin, TX 78701", "2026-09-20T14:30:00Z", "2026-09-26", None, 1, 1, None),
    ("order-1003", "CS-1003", "cust-sam", "delivered", "paid", 12000, 0, "USD", "7 Oak Road, Portland, OR 97205", "2026-09-02T09:00:00Z", "2026-09-07", "2026-09-06T16:42:00Z", 0, 1, "Customer reported the item arrived damaged."),
    ("order-1004", "CS-1004", "cust-alex", "refunded", "refunded", 3000, 0, "USD", "12 Market Street, Seattle, WA 98101", "2026-08-15T12:00:00Z", None, "2026-08-22T11:05:00Z", 0, 0, "Refund completed to original payment method."),
]

ORDER_ITEMS = [
    ("item-1001a", "order-1001", "HEAD-001", "Wireless Headphones", 1, 8999),
    ("item-1002a", "order-1002", "MUG-002", "Insulated Travel Mug", 2, 2250),
    ("item-1003a", "order-1003", "LAMP-003", "Desk Lamp", 1, 12000),
    ("item-1004a", "order-1004", "BAG-004", "Everyday Tote Bag", 1, 3000),
]

ORDER_EVENTS = [
    ("event-1001a", "order-1001", "order_placed", "2026-09-18T10:15:00Z", None, "Order confirmed."),
    ("event-1001b", "order-1001", "shipped", "2026-09-20T08:00:00Z", "Seattle, WA", "Package handed to carrier."),
    ("event-1002a", "order-1002", "order_placed", "2026-09-20T14:30:00Z", None, "Order confirmed and awaiting fulfillment."),
    ("event-1003a", "order-1003", "delivered", "2026-09-06T16:42:00Z", "Portland, OR", "Delivered to the shipping address."),
    ("event-1004a", "order-1004", "refund_issued", "2026-08-22T11:05:00Z", None, "Refund issued to the original payment method."),
]

ARTICLES = [
    ("article-shipping", "shipping-and-delivery", "Shipping and delivery", "shipping", "Most orders are delivered within the date shown in the order details. Tracking events are updated after a carrier scan."),
    ("article-cancellation", "cancelling-an-order", "Cancelling an order", "cancellation", "Orders can be cancelled only while they are marked cancellation eligible. Orders already packed or shipped require human support review."),
    ("article-returns", "returns-and-damaged-items", "Returns and damaged items", "returns", "Unused items may be returned during the eligible return window. Damaged-item reports require a human support agent to review the claim."),
    ("article-refunds", "refund-timing", "Refund timing", "refunds", "Approved refunds are sent to the original payment method. Refund timing can vary by financial institution."),
]


def seed(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.executemany("INSERT OR REPLACE INTO customers (id, full_name, email) VALUES (?, ?, ?)", CUSTOMERS)
        connection.executemany(
            """INSERT OR REPLACE INTO orders
            (id, order_number, customer_id, status, payment_status, subtotal_cents, shipping_cents, currency,
             shipping_address, placed_at, estimated_delivery_date, delivered_at, cancellation_eligible, return_eligible, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ORDERS,
        )
        connection.executemany("INSERT OR REPLACE INTO order_items VALUES (?, ?, ?, ?, ?, ?)", ORDER_ITEMS)
        connection.executemany("INSERT OR REPLACE INTO order_events VALUES (?, ?, ?, ?, ?, ?)", ORDER_EVENTS)
        connection.executemany("INSERT OR REPLACE INTO knowledge_articles (id, slug, title, category, content) VALUES (?, ?, ?, ?, ?)", ARTICLES)
        connection.commit()


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATABASE_PATH
    seed(target)
    print(f"Seeded {target}")
