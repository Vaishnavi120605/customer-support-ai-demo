# Customer chat UI

The Streamlit customer-chat foundation for the Customer Support AI demo.

It currently keeps a browser-session message history, captures order context, and
shows the human-handoff state. It uses deterministic placeholder replies only;
Azure AI Foundry and SQLite integrations will be added by their respective
application layers.

## Run locally

```bash
python -m pip install -r ui/requirements.txt
streamlit run ui/app.py
```

## Integration seams

- Replace `placeholder_response()` with the Foundry agent client call.
- Replace session-state persistence with the conversation/message repository.
- When `needs_handoff()` is true, create a handoff ticket and fetch its current
  status instead of using the local status placeholder.
