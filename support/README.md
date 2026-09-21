# Human support console

This Streamlit console is the staff side of the customer-support AI demo. It uses
the same SQLite database as the customer application and intentionally makes no
Azure AI Foundry calls.

## Run locally

From the repository root, create the deterministic demo database once:

```bash
python database/seed.py
```

Install the project requirements, then start the console:

```bash
pip install -r requirements.txt
streamlit run support/console.py
```

The default database is `database/customer_support_demo.db`. To use a different
database, set `SUPPORT_DATABASE_PATH` before launching Streamlit:

```bash
SUPPORT_DATABASE_PATH=/absolute/path/customer_support.db streamlit run support/console.py
```

## Workflow

1. Filter the support queue by ticket status or priority.
2. Select a ticket to read the AI summary and complete persisted transcript.
3. Enter a specialist name and assign the request.
4. Send a human reply. This writes a `human` message, assigns the ticket, and
   sets it to `waiting_customer`.
5. Resolve the ticket when the request is complete. The ticket and conversation
   become `resolved`; all staff actions are recorded in `audit_events`.

Handoff tickets are created by the customer/AI integration. The seed database
contains orders and policies but no artificial support tickets, so an empty queue
after seeding is expected.
