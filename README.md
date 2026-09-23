# Customer Support AI Demo

A portfolio-ready demonstration of an AI customer-support chat experience for order questions. It uses Microsoft Foundry (Azure AI Foundry), Streamlit, and SQLite, and transfers conversations to a human support agent when the request needs human judgment.

## Project presentation

- [View the presentation as a PDF](docs/Acme-Support-Project-Presentation.pdf)
- [Download the editable PowerPoint](docs/Acme-Support-Project-Presentation.pptx)

The 12-slide presentation covers the application architecture, customer chat, human handoff, support workflow, demo walkthrough, verification, and future improvements.

## Goals

- Answer grounded order and policy questions.
- Look up verified order data rather than inventing facts.
- Escalate uncertain, exceptional, or explicitly human-requested cases.
- Give a support representative the conversation context and AI summary.
- Demonstrate a complete, auditable handoff loop.

## Architecture

```text
Customer → Streamlit customer chat → Foundry prompt agent
                                      ├─ order lookup tool → SQLite
                                      ├─ FAQ / policy knowledge
                                      └─ escalation decision → SQLite support queue
                                                                  ↓
                                                        Streamlit support console
                                                                  ↓
                                                         customer receives reply
```

## Technology

| Area | Choice |
| --- | --- |
| UI | Streamlit |
| AI | Microsoft Foundry Agent Service / prompt agent |
| Data | SQLite |
| Identity | Azure identity for Foundry; demo support role in Streamlit |
| Quality | Foundry tracing and evaluations plus application logs |

## Handoff policy

Escalate when the customer asks for a human, the agent cannot find grounded information, an order is missing, the request involves a refund or other exception, a payment dispute, address changes after dispatch, a damaged-item claim, an unsafe request, or low confidence.

Each ticket stores its reason, priority, customer and order context, transcript, AI summary, owner, timestamps, and state. Expected lifecycle: `open → assigned → waiting_customer → resolved`.

## Delivery plan

### Phase 1 — Foundations

Define supported queries, policy boundaries, escalation rules, demo scenarios, seed orders, and Foundry resources.

### Phase 2 — AI capability

Configure the prompt agent, tools, policy grounding, order lookup, and escalation behavior.

### Phase 3 — Customer experience

Build the Streamlit chat, streaming response experience, conversation persistence, and safe order context.

### Phase 4 — Human handoff

Build ticket creation, support queue, transcript summary, assignment, human replies, and resolution states.

### Phase 5 — Quality and demo readiness

Add logging, evaluation cases, safety tests, error handling, setup documentation, and a repeatable demo script.

## Data model

- `customers`: demo customer records.
- `orders`: order number, items, payment state, status, and dates.
- `order_events`: fulfillment and tracking history.
- `knowledge_articles`: support policy and FAQ content.
- `conversations` and `messages`: customer, AI, and human chat history.
- `handoff_tickets`: queue, assignment, priority, and resolution data.
- `audit_events`: tool calls and support actions.

## Definition of done

- The agent never invents order facts.
- Every escalation includes a usable context summary and full transcript.
- A human reply appears in the customer's existing conversation.
- The demo covers order status, a delivery question, a policy FAQ, a missing order, and a human-only refund exception.

## Issue plan

The GitHub issues in this repository are ordered by phase and describe the implementation backlog. Start with the foundation issues before building application features.

## Local setup

1. Create and activate a Python virtual environment.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and confirm the non-secret Foundry endpoint, model deployment name, and agent name.
4. Authenticate to Azure locally with `az login`; do not add credentials to `.env`.
5. Seed the demo database with `python3 database/seed.py`.
6. Start the customer UI with `streamlit run ui/app.py`.
7. In another terminal, start the human console with `streamlit run support/console.py`.

## Security

This project uses Azure identity (`DefaultAzureCredential`) for Foundry access. `.env`, SQLite runtime files, and Streamlit secrets are ignored by Git.
