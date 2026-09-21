# Azure AI Foundry integration

This directory contains the integration boundary for the `customer-support-agent`.
It is intentionally independent from Streamlit and SQLite persistence code.

## Local configuration

Use Azure CLI login for local development:

```bash
az login
python -m pip install -r foundry/requirements.txt
export FOUNDRY_PROJECT_ENDPOINT='https://customer-support-ai-dem-resource.services.ai.azure.com/api/projects/customer-support-ai-demo'
export MODEL_DEPLOYMENT_NAME='gpt-4.1-mini'
export FOUNDRY_AGENT_NAME='customer-support-agent'
```

`DefaultAzureCredential` will then authenticate through the Azure CLI session.
In hosted environments, configure an appropriate managed or workload identity with
the required Azure AI Foundry role. Do not use account keys, API keys, access
tokens, or client secrets in source files or `.env` files.

## Agent instructions

`agent_instructions.py` is the version-controlled baseline prompt to paste into
the Foundry prompt agent or use during later agent-provisioning work. It requires
verified order-tool data and defines mandatory human-handoff cases.

## Order lookup tool contract

The application will expose a Foundry function tool named `order_lookup`.

Input:

```json
{"order_number":"ORD-1001","customer_email":"customer@example.test"}
```

`customer_email` is optional at the contract boundary, but the SQLite
implementation must require sufficient verification before returning any details.
The tool must use parameterized SQL, return only fields represented by
`OrderLookupResult`, and never return payment data, addresses, internal notes, or
other customer records.

If an order cannot be verified, it returns `found: false`, `status: "unknown"`,
and a safe explanatory `message`. The agent must then offer human handoff.

The typed contract in `order_lookup_contract.py` is provider-neutral. A later
issue will adapt it to the Azure Foundry function-tool schema and implement the
SQLite-backed lookup.
