"""Customer-facing Streamlit chat shell for the support AI demo.

This module intentionally has no database or Azure AI dependencies.  It owns only
the presentation layer and exposes clear integration points for those services.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.seed import seed
from foundry.runtime import FoundryInvocationError, ask_support_agent
from services.support_service import OrderDetails, SupportService


PAGE_TITLE = "Acme Support"
HANDOFF_TRIGGERS = (
    "human",
    "person",
    "agent",
    "bot",
    "representative",
    "speak to someone",
    "talk to someone",
    "refund exception",
    "payment dispute",
    "damaged",
    "address change",
)
DATABASE_PATH = PROJECT_ROOT / "database" / "customer_support_demo.db"


def initialise_session() -> None:
    """Set defaults and restore a conversation selected by the browser URL."""
    st.session_state.setdefault(
        "messages",
        [
            {
                "role": "assistant",
                "content": "Hi! I can help with orders, delivery, returns, and store policies. What can I look into?",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        ],
    )
    st.session_state.setdefault("handoff_status", "AI support is handling this conversation")
    st.session_state.setdefault("handoff_requested", False)
    if not DATABASE_PATH.exists():
        seed(DATABASE_PATH)
    service = SupportService(DATABASE_PATH)
    saved_conversation_id = st.query_params.get("conversation")
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = saved_conversation_id or service.create_conversation()

    # Restore handoff state from SQLite after a browser refresh.
    ticket = service.get_handoff_for_conversation(st.session_state.conversation_id)
    if ticket is not None:
        st.session_state.handoff_requested = True
        st.session_state.handoff_status = (
            f"A human support specialist is handling this conversation (ticket {ticket.id[:8]})."
        )

    # The identifier lets this browser reopen the same database transcript.
    if saved_conversation_id != st.session_state.conversation_id:
        st.query_params["conversation"] = st.session_state.conversation_id


def add_message(role: str, content: str) -> None:
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )


def needs_handoff(message: str) -> bool:
    message = message.lower()
    return any(trigger in message for trigger in HANDOFF_TRIGGERS)


def order_context(order: OrderDetails | None) -> str:
    """Format only customer-safe order fields for the remote AI request."""
    if order is None:
        return "No verified order was found for the supplied order number and email."
    events = "; ".join(
        f"{event['event_type']} on {event['event_at']}: {event['details']}"
        for event in order.events
    ) or "No event history available."
    items = ", ".join(
        f"{item['quantity']}× {item['product_name']}" for item in order.items
    ) or "No item details available."
    return (
        f"Verified order context: order={order.order_number}; status={order.status}; "
        f"estimated delivery={order.estimated_delivery_date or 'not available'}; "
        f"delivered={order.delivered_at or 'not delivered'}; "
        f"cancellation eligible={order.cancellation_eligible}; return eligible={order.return_eligible}; "
        f"items={items}; events={events}"
    )


def request_handoff(service: SupportService, reason: str, summary: str, priority: str = "normal") -> str:
    """Create an idempotent queue item and return its identifier."""
    ticket = service.create_handoff(
        st.session_state.conversation_id, reason=reason, ai_summary=summary, priority=priority
    )
    st.session_state.handoff_requested = True
    st.session_state.handoff_status = (
        f"Your request is queued for a support specialist (ticket {ticket.id[:8]}). "
        "They will reply in this chat."
    )
    return ticket.id


def agent_requested_handoff(response: str) -> bool:
    """Detect a Foundry response that promises transfer to a human.

    The local queue is the source of truth for the support console. If the
    remote agent says it is transferring a customer, this creates the matching
    SQLite ticket even when the customer used unexpected wording.
    """
    normalized = response.lower()
    signals = (
        "connecting you to a human",
        "connect you with a human",
        "human support agent",
        "human support specialist",
        "transfer you to a human",
    )
    return any(signal in normalized for signal in signals)


def render_handoff_banner() -> None:
    status = st.session_state.handoff_status
    if st.session_state.handoff_requested:
        st.warning(f"🧑‍💼 **Human support requested** — {status}")
    else:
        st.info(f"✨ **Support status:** {status}")


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="💬", layout="wide")
    initialise_session()

    st.markdown(
        """
        <style>
        .block-container {max-width: 980px; padding-top: 2.25rem;}
        [data-testid="stChatMessage"] {border-radius: 14px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Acme Support")
        st.caption("Customer support AI demo")
        st.divider()
        st.subheader("Order context")
        order_number = st.text_input(
            "Order number",
            placeholder="e.g. ORD-1042",
            help="This will be used by the order-lookup tool once it is connected.",
        ).strip()
        email = st.text_input("Email address (optional)", placeholder="you@example.com").strip()
        st.caption("Your details are used only to find the relevant order.")

        st.divider()
        st.subheader("Conversation")
        st.caption(f"{len(st.session_state.messages)} messages in this session")
        if st.button("Start a new chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.handoff_requested = False
            st.session_state.handoff_status = "AI support is handling this conversation"
            st.session_state.conversation_id = SupportService(DATABASE_PATH).create_conversation()
            st.query_params["conversation"] = st.session_state.conversation_id
            add_message("assistant", "New conversation started. How can I help today?")
            st.rerun()

    st.title("How can we help?")
    st.caption("Ask about an order, delivery, returns, or a support policy.")
    render_handoff_banner()

    service = SupportService(DATABASE_PATH)
    persisted_messages = service.list_messages(st.session_state.conversation_id)
    if persisted_messages:
        role_map = {"customer": "user", "ai": "assistant", "human": "assistant", "system": "assistant"}
        for message in persisted_messages:
            with st.chat_message(role_map[message["sender_type"]]):
                if message["sender_type"] == "human":
                    st.caption("Human support")
                st.markdown(message["body"])
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    prompt = st.chat_input("Type your question…")
    if not prompt:
        return

    add_message("user", prompt)
    service.add_message(st.session_state.conversation_id, "customer", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if needs_handoff(prompt):
            request_handoff(
                service,
                reason="Customer requested human support or a human-only exception.",
                summary=f"Customer message: {prompt}",
                priority="high" if any(term in prompt.lower() for term in ("refund", "payment", "damaged")) else "normal",
            )
            reply = (
                "I’m connecting you with a human support specialist. I’ve kept your order context and chat "
                "history ready for them."
            )
        else:
            try:
                order = None
                if order_number:
                    order = service.lookup_order(order_number, email or None)
                    if order is None:
                        request_handoff(
                            service,
                            reason="Order could not be verified with the supplied details.",
                            summary=f"Customer asked: {prompt}. Order input: {order_number}.",
                        )
                        reply = (
                            "I couldn’t verify that order from the details provided, so I’ve asked a human "
                            "support specialist to help."
                        )
                    else:
                        reply = ask_support_agent(f"{order_context(order)}\n\nCustomer question: {prompt}")
                else:
                    reply = ask_support_agent(f"Customer question: {prompt}")
                if agent_requested_handoff(reply):
                    request_handoff(
                        service,
                        reason="Foundry agent determined that human support is required.",
                        summary=f"Customer message: {prompt}\n\nAI response: {reply}",
                        priority="normal",
                    )
            except (FoundryInvocationError, ValueError) as error:
                request_handoff(
                    service,
                    reason="AI service or order lookup could not provide a grounded answer.",
                    summary=f"Customer asked: {prompt}. Technical category: {type(error).__name__}.",
                )
                reply = (
                    "I’m unable to give you a verified answer right now, so I’ve connected you with a "
                    "human support specialist."
                )
        st.markdown(reply)
    add_message("assistant", reply)
    service.add_message(st.session_state.conversation_id, "ai", reply)


if __name__ == "__main__":
    main()
