# Customer Support AI Demo

A demo customer-support assistant for order questions, built with Streamlit, SQLite, and Microsoft Foundry. It answers grounded questions, looks up verified order data, and hands off exceptions to a human-support queue.

## Current work

The repository is being implemented in the order documented by its GitHub issues: SQLite data foundations, Foundry agent configuration, customer chat, then human handoff and evaluation.

## Local setup

1. Create and activate a Python virtual environment.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and confirm the non-secret Foundry endpoint, model deployment name, and agent name.
4. Authenticate to Azure locally with `az login`; do not add credentials to `.env`.
5. Run the database seed command and start the Streamlit app once the UI integration is completed.

## Security

This project uses Azure identity (`DefaultAzureCredential`) for Foundry access. `.env`, SQLite runtime files, and Streamlit secrets are ignored by Git.
