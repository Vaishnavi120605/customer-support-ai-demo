# Demo database

This directory owns the SQLite schema and deterministic demo fixtures for the customer-support scenario. It intentionally contains no credentials and no application UI code.

Create a local database:

```bash
python database/seed.py
```

The resulting `customer_support_demo.db` is local-only and ignored by Git. To verify schema constraints and the representative data set:

```bash
python database/verify.py
```

The fixtures cover a shipped order, a cancellable processing order, a damaged delivered order that should be handed to a human, and a completed refund. The schema also reserves tables for conversations, messages, handoff tickets, and audit events so later application phases can persist the full support workflow.
