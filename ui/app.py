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
from services.chat_style import CHAT_STYLE


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
AI_SWITCH_TRIGGERS = (
    "switch to ai",
    "back to ai",
    "talk to ai",
    "speak to ai",
    "i want ai",
    "want ai",
    "ai assistant",
    "ai support",
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

    # A saved URL can outlive its local SQLite database (for example, after a
    # user runs seed.py again or opens a newly extracted copy of the project).
    # Treat that old identifier as a new chat rather than showing a traceback.
    try:
        service.get_support_mode(st.session_state.conversation_id)
    except LookupError:
        st.session_state.conversation_id = service.create_conversation()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I can help with orders, delivery, returns, and store policies. What can I look into?",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        ]

    # Restore the customer-selected support mode after a browser refresh.
    ticket = service.get_handoff_for_conversation(st.session_state.conversation_id)
    if service.get_support_mode(st.session_state.conversation_id) == "human":
        st.session_state.handoff_requested = True
        st.session_state.handoff_status = (
            f"A human support specialist is handling this conversation (ticket {ticket.id[:8]})."
        )
    else:
        st.session_state.handoff_requested = False
        st.session_state.handoff_status = "AI support is handling this conversation"

    # The identifier lets this browser reopen the same database transcript.
    if saved_conversation_id != st.session_state.conversation_id:
        st.query_params["conversation"] = st.session_state.conversation_id

    saved_context = service.get_conversation_context(st.session_state.conversation_id)
    st.session_state.setdefault("order_number_input", saved_context["order_number"])
    st.session_state.setdefault("email_input", saved_context["email"])


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


def requests_ai_support(message: str) -> bool:
    """Recognize an explicit request to leave human support and return to AI."""
    normalized = message.lower()
    return any(trigger in normalized for trigger in AI_SWITCH_TRIGGERS)


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
        st.markdown(
            f"""<div class="support-state human-state">
            <div class="state-icon">◉</div><div><span>HUMAN SUPPORT</span><strong>{status}</strong></div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""<div class="support-state ai-state">
            <div class="state-icon">✦</div><div><span>AI ASSISTANT ACTIVE</span><strong>{status}</strong></div>
            </div>""",
            unsafe_allow_html=True,
        )


def switch_to_ai(service: SupportService) -> None:
    """Return control to AI after the customer explicitly chooses it."""
    service.switch_to_ai(st.session_state.conversation_id)
    st.session_state.handoff_requested = False
    st.session_state.handoff_status = "AI support is handling this conversation"
    reply = "AI support is active again. How can I help?"
    add_message("assistant", reply)
    service.add_message(st.session_state.conversation_id, "system", reply)


def start_new_chat() -> None:
    """Create a fresh chat and clear its locally saved order context."""
    st.session_state.messages = []
    st.session_state.handoff_requested = False
    st.session_state.handoff_status = "AI support is handling this conversation"
    st.session_state.conversation_id = SupportService(DATABASE_PATH).create_conversation()
    st.session_state.order_number_input = ""
    st.session_state.email_input = ""
    st.query_params["conversation"] = st.session_state.conversation_id
    add_message("assistant", "New conversation started. How can I help today?")


@st.fragment(run_every="2s")
def poll_for_human_reply() -> None:
    """Rerun the page when a specialist posts the awaited next reply."""
    service = SupportService(DATABASE_PATH)
    ticket = service.get_handoff_for_conversation(st.session_state.conversation_id)
    if ticket is None or ticket.status not in {"open", "assigned"}:
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="💬", layout="wide")
    initialise_session()

    st.markdown(
        """
        <style>
        :root { --ink: #f8fafc; --muted: #98a5b8; --panel: #121a2a; --line: #26344e;
        --blue: #5da9ff; --violet: #8b75ff; --mint: #61dfbc; }
        .stApp { background: radial-gradient(circle at 80% -8%, #18356a 0, transparent 32%),
                 radial-gradient(circle at 14% 5%, #272153 0, transparent 26%), #090f1d; color: var(--ink); }
        .block-container {max-width: 1080px; padding-top: 2rem; padding-bottom: 7rem;}
        [data-testid="stSidebar"] {background: linear-gradient(180deg, #101829 0%, #0c1220 100%); border-right: 1px solid var(--line);}
        [data-testid="stSidebar"] > div:first-child {padding-top: 1.5rem;}
        [data-testid="stSidebar"] .stTextInput input {background: #0a1020; border: 1px solid #2a3955; border-radius: 10px; color: #fff;}
        [data-testid="stChatMessage"] {border: 1px solid #24314a; border-radius: 18px; padding: 1rem 1.1rem; margin: .75rem 0; background: rgba(18, 26, 42, .88); box-shadow: 0 12px 35px rgba(0,0,0,.12);}
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {background: linear-gradient(125deg, #18284a, #172440); border-color: #35578d;}
        [data-testid="stChatInput"] {border-radius: 16px; border: 1px solid #344d76; background: #111a2b; box-shadow: 0 16px 45px rgba(0,0,0,.3);}
        [data-testid="stChatInput"] textarea {color: #fff;}
        .stButton > button {border-radius: 10px; min-height: 2.55rem; border: 1px solid #3b5682; background: linear-gradient(135deg, #1b3157, #182b4a); color: #f8fbff; font-weight: 650;}
        .stButton > button:hover {border-color: #78b5ff; color: white; transform: translateY(-1px);}
        .brand-kicker, .eyebrow {font-size: .72rem; font-weight: 800; letter-spacing: .14em; color: #8ebfff;}
        .brand-name {font-size: 1.45rem; font-weight: 800; letter-spacing: -.04em; margin: .25rem 0;}
        .brand-copy {font-size: .82rem; color: var(--muted); line-height: 1.45;}
        .hero {padding: 1.9rem 2rem; border-radius: 22px; border: 1px solid rgba(121, 167, 255, .32); background: linear-gradient(120deg, rgba(30, 57, 104, .92), rgba(22, 28, 60, .92)); box-shadow: 0 22px 55px rgba(2,7,20,.25); margin-bottom: 1.15rem;}
        .hero h1 {font-size: clamp(2rem, 4vw, 3.45rem); letter-spacing: -.06em; margin: .45rem 0 .55rem; line-height: 1;}
        .hero p {margin: 0; color: #b9c7dd; font-size: 1rem;}
        .support-state {display: flex; align-items: center; gap: .85rem; padding: .95rem 1.05rem; margin: .75rem 0 1.25rem; border-radius: 14px; border: 1px solid;}
        .support-state .state-icon {width: 2rem; height: 2rem; display:grid; place-items:center; border-radius: 50%; font-weight:800;}
        .support-state span {display:block; font-size:.67rem; letter-spacing:.1em; font-weight:800; margin-bottom:.15rem;}
        .support-state strong {font-size:.88rem; font-weight:600;}
        .ai-state {background: rgba(20, 74, 119, .38); border-color:#2e6ca5;}.ai-state .state-icon {background:#1c5c95; color:#aee3ff;}.ai-state span {color:#83caff;}
        .human-state {background: rgba(103, 82, 20, .38); border-color:#8f7a30;}.human-state .state-icon {background:#806c26; color:#fff0a5;}.human-state span {color:#f4dc70;}
        .sidebar-card {padding: .85rem; border: 1px solid #26344e; border-radius: 12px; background: rgba(19, 29, 47, .72); margin: .65rem 0 1rem; color: #aebbd0; font-size: .8rem; line-height:1.5;}
        .sidebar-card b {display:block; color:#ecf3ff; font-size:.78rem; margin-bottom:.2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(CHAT_STYLE, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("<div class='brand-kicker'>ACME / CUSTOMER CARE</div><div class='brand-name'>Acme Support</div><div class='brand-copy'>A faster way to get order help, built for calm conversations.</div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-card'><b>Secure order help</b>Your order details are checked before the assistant shares information.</div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("Order context")
        order_number = st.text_input(
            "Order number",
            placeholder="e.g. ORD-1042",
            help="This will be used by the order-lookup tool once it is connected.",
            key="order_number_input",
        ).strip()
        email = st.text_input("Email address (optional)", placeholder="you@example.com", key="email_input").strip()
        service = SupportService(DATABASE_PATH)
        service.save_conversation_context(st.session_state.conversation_id, order_number, email)
        st.caption("Saved locally for this chat and used only to verify the relevant order.")

        st.divider()
        st.subheader("Conversation")
        st.caption(f"{len(st.session_state.messages)} messages in this session")
        st.button("Start a new chat", use_container_width=True, on_click=start_new_chat)

    st.markdown("""<section class="hero"><div class="eyebrow">ACME CARE DESK</div><h1>How can we help?</h1><p>Ask about an order, delivery, returns, or a support policy.</p></section>""", unsafe_allow_html=True)
    render_handoff_banner()

    service = SupportService(DATABASE_PATH)
    persisted_messages = service.list_messages(st.session_state.conversation_id)
    handoff_ticket = service.get_handoff_for_conversation(st.session_state.conversation_id)
    last_persisted_sender = persisted_messages[-1]["sender_type"] if persisted_messages else None
    awaiting_human_reply = (
        service.get_support_mode(st.session_state.conversation_id) == "human"
        and handoff_ticket is not None
        and handoff_ticket.status in {"open", "assigned"}
        # A human reply always hands the next turn back to the customer. This
        # UI-level check keeps the transcript and the input state consistent
        # even during the brief refresh interval between the two browser tabs.
        and last_persisted_sender != "human"
    )
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

    if awaiting_human_reply:
        # The fragment polls SQLite every two seconds. When the specialist
        # replies, the page reruns, displays that one reply, and unlocks input.
        poll_for_human_reply()
        st.info("Your message is with human support. Their reply will appear automatically.")
        if st.button("Switch back to AI", use_container_width=True):
            switch_to_ai(service)
            st.rerun()

    prompt = st.chat_input(
        "Waiting for human support…" if awaiting_human_reply else "Type your question…",
        disabled=awaiting_human_reply,
    )
    if not prompt:
        return

    add_message("user", prompt)
    service.add_message(st.session_state.conversation_id, "customer", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    if service.get_support_mode(st.session_state.conversation_id) == "human":
        if requests_ai_support(prompt):
            switch_to_ai(service)
            reply = st.session_state.messages[-1]["content"]
            with st.chat_message("assistant"):
                st.markdown(reply)
        # In human mode, ordinary customer messages are saved above for the
        # specialist. The AI intentionally remains silent.
        st.rerun()
        return

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
    if service.get_support_mode(st.session_state.conversation_id) == "human":
        st.rerun()


if __name__ == "__main__":
    main()
