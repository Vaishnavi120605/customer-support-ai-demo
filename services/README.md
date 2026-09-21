# Service layer

`SupportService` is the framework-independent SQLite boundary for the customer-support demo. It is intentionally separate from both Streamlit and Azure AI Foundry so each can be developed and tested independently.

## Capabilities

- `lookup_order(order_number, customer_email=None)` validates `CS-` order numbers and, when an email is supplied, returns order data only to the owning customer. Its `OrderDetails` result excludes shipping addresses and payment details.
- `create_conversation(customer_id=None)` and `add_message(...)` persist a transcript.
- `create_handoff(...)` adds a human-support ticket, moves the conversation to `awaiting_human`, and writes an audit event. It is idempotent for a conversation: a second call returns the original ticket instead of duplicating it.

The database must first be initialized with `database/schema.sql` (or the supplied seed script).

## Verify

From the repository root:

```bash
python services/verify.py
```

The script creates and seeds a temporary database, so it does not modify the demo database or require Azure credentials.
