"""Customer-facing Streamlit chat shell for the support AI demo.

This module intentionally has no database or Azure AI dependencies.  It owns only
the presentation layer and exposes clear integration points for those services.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st


PAGE_TITLE = "Acme Support"
HANDOFF_TRIGGERS = (
    "human",
    "person",
    "agent",
    "refund exception",
    "payment dispute",
    "damaged",
    "address change",
)


def initialise_session() -> None:
    """Set defaults once per browser session."""
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


def placeholder_response(order_number: str | None) -> str:
    """Temporary response until the Foundry agent service is connected."""
    context = f" for order **{order_number}**" if order_number else ""
    return (
        f"I have your question{context}. This demo screen is ready to connect to the "
        "Azure AI Foundry agent; its live answer will appear here once the service is wired in."
    )


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
            add_message("assistant", "New conversation started. How can I help today?")
            st.rerun()

    st.title("How can we help?")
    st.caption("Ask about an order, delivery, returns, or a support policy.")
    render_handoff_banner()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Type your question…")
    if not prompt:
        return

    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if needs_handoff(prompt):
            st.session_state.handoff_requested = True
            st.session_state.handoff_status = (
                "Your request is queued for a support specialist. They will review this chat and reply here."
            )
            reply = (
                "I’m connecting you with a human support specialist. I’ve kept your order context and chat "
                "history ready for them."
            )
        else:
            reply = placeholder_response(order_number or None)
        st.markdown(reply)
    add_message("assistant", reply)


if __name__ == "__main__":
    main()
