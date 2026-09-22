"""Streamlit console for support specialists.

Run with::

    streamlit run support/console.py

The console deliberately talks only to SQLite. It has no Azure AI dependency:
the customer-facing service is responsible for creating a handoff ticket.
"""

from __future__ import annotations

import os
import sys
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from services.chat_style import CHAT_STYLE, navigation
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "database" / "customer_support_demo.db"
TICKET_STATUSES = ("open", "assigned", "waiting_customer", "resolved")
PRIORITIES = ("low", "normal", "high", "urgent")


def database_path() -> Path:
    """Return the configured database location without creating it."""
    raw_path = os.getenv("SUPPORT_DATABASE_PATH")
    return Path(raw_path).expanduser() if raw_path else DEFAULT_DATABASE_PATH


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open a row-oriented SQLite connection with foreign keys enabled."""
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def add_audit_event(connection: sqlite3.Connection, conversation_id: str, event_type: str, detail: str) -> None:
    connection.execute(
        """INSERT INTO audit_events (id, conversation_id, event_type, actor_type, detail, created_at)
        VALUES (?, ?, ?, 'human', ?, ?)""",
        (str(uuid.uuid4()), conversation_id, event_type, detail, utc_now()),
    )


def list_tickets(status: str, priority: str) -> list[sqlite3.Row]:
    clauses: list[str] = []
    values: list[str] = []
    if status != "all":
        clauses.append("t.status = ?")
        values.append(status)
    if priority != "all":
        clauses.append("t.priority = ?")
        values.append(priority)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT t.*, c.full_name, c.email,
               (SELECT body FROM messages m WHERE m.conversation_id = t.conversation_id
                ORDER BY m.rowid DESC LIMIT 1) AS latest_message
        FROM handoff_tickets t
        LEFT JOIN conversations cv ON cv.id = t.conversation_id
        LEFT JOIN customers c ON c.id = cv.customer_id
        {where}
        ORDER BY CASE t.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,
                 t.created_at ASC
    """
    with connect() as connection:
        return connection.execute(query, values).fetchall()


def get_ticket(ticket_id: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            """SELECT t.*, c.full_name, c.email, cv.status AS conversation_status
               FROM handoff_tickets t
               JOIN conversations cv ON cv.id = t.conversation_id
               LEFT JOIN customers c ON c.id = cv.customer_id
               WHERE t.id = ?""",
            (ticket_id,),
        ).fetchone()


def get_messages(conversation_id: str) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """SELECT sender_type, body, created_at FROM messages
               WHERE conversation_id = ? ORDER BY rowid ASC""",
            (conversation_id,),
        ).fetchall()


def assign_ticket(ticket_id: str, assignee: str) -> None:
    assignee = assignee.strip()
    if not assignee:
        raise ValueError("Enter the name of the support specialist.")
    with connect() as connection:
        ticket = connection.execute(
            "SELECT conversation_id, status FROM handoff_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        if ticket is None:
            raise ValueError("This ticket no longer exists.")
        if ticket["status"] == "resolved":
            raise ValueError("This ticket is closed because the customer switched back to AI support.")
        if ticket["status"] == "waiting_customer":
            raise ValueError("Wait for the customer's next message before changing the assignment.")
        connection.execute("UPDATE handoff_tickets SET assigned_to = ?, status = 'assigned' WHERE id = ?", (assignee, ticket_id))
        add_audit_event(connection, ticket["conversation_id"], "ticket_assigned", f"Assigned to {assignee}.")


def post_reply(ticket_id: str, body: str, specialist: str) -> None:
    body, specialist = body.strip(), specialist.strip()
    if not body:
        raise ValueError("Write a reply before sending it.")
    if not specialist:
        raise ValueError("Enter your name before sending a reply.")
    with connect() as connection:
        ticket = connection.execute(
            """SELECT t.conversation_id, t.status, cv.support_mode
               FROM handoff_tickets t JOIN conversations cv ON cv.id = t.conversation_id
               WHERE t.id = ?""",
            (ticket_id,),
        ).fetchone()
        if ticket is None:
            raise ValueError("This ticket no longer exists.")
        if ticket["status"] == "resolved":
            raise ValueError("Reopen the ticket before replying.")
        if ticket["status"] == "waiting_customer":
            raise ValueError("Wait for the customer’s next message before sending another reply.")
        if ticket["support_mode"] != "human":
            raise ValueError("The customer is using AI support now, so a human reply cannot be sent.")
        now = utc_now()
        connection.execute(
            "INSERT INTO messages (id, conversation_id, sender_type, body, created_at) VALUES (?, ?, 'human', ?, ?)",
            (str(uuid.uuid4()), ticket["conversation_id"], body, now),
        )
        connection.execute(
            "UPDATE handoff_tickets SET assigned_to = ?, status = 'waiting_customer' WHERE id = ?",
            (specialist, ticket_id),
        )
        connection.execute("UPDATE conversations SET status = 'active', updated_at = ? WHERE id = ?", (now, ticket["conversation_id"]))
        add_audit_event(connection, ticket["conversation_id"], "human_reply_sent", f"Reply sent by {specialist}.")


def resolve_ticket(ticket_id: str, specialist: str) -> None:
    specialist = specialist.strip()
    if not specialist:
        raise ValueError("Enter your name before resolving a ticket.")
    with connect() as connection:
        ticket = connection.execute("SELECT conversation_id FROM handoff_tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            raise ValueError("This ticket no longer exists.")
        now = utc_now()
        connection.execute(
            "UPDATE handoff_tickets SET assigned_to = ?, status = 'resolved', resolved_at = ? WHERE id = ?",
            (specialist, now, ticket_id),
        )
        connection.execute("UPDATE conversations SET status = 'resolved', updated_at = ? WHERE id = ?", (now, ticket["conversation_id"]))
        add_audit_event(connection, ticket["conversation_id"], "ticket_resolved", f"Resolved by {specialist}.")


def render_ticket_list(tickets: list[sqlite3.Row]) -> str | None:
    if not tickets:
        st.info("No handoff tickets match these filters.")
        return None
    labels = {
        row["id"]: f"{row['priority'].upper()} · {row['status']} · {row['full_name'] or 'Unknown customer'} · {row['reason'][:55]}"
        for row in tickets
    }
    return st.radio("Support queue", options=list(labels), format_func=labels.get, label_visibility="collapsed")


def render_transcript(conversation_id: str) -> None:
    st.subheader("Conversation transcript")
    messages = get_messages(conversation_id)
    if not messages:
        st.caption("No messages have been stored for this conversation yet.")
        return
    role_labels = {"customer": "Customer", "ai": "AI", "human": "Human support", "system": "System"}
    for message in messages:
        with st.chat_message("assistant" if message["sender_type"] in {"ai", "human", "system"} else "user"):
            st.caption(f"{role_labels[message['sender_type']]} · {message['created_at']}")
            st.markdown(message["body"])


@st.fragment(run_every="2s")
def poll_inbox(snapshot: tuple) -> None:
    """Refresh the inbox when messages or ticket states change."""
    with connect() as connection:
        current = (
            tuple(connection.execute("SELECT COUNT(*), MAX(rowid) FROM messages").fetchone()),
            tuple(tuple(row) for row in connection.execute(
                "SELECT id, status, assigned_to FROM handoff_tickets ORDER BY id"
            )),
        )
    if current != snapshot:
        st.rerun(scope="app")


def main() -> None:
    st.set_page_config(page_title="Acme Support Console", page_icon="🧑‍💼", layout="wide")
    st.markdown(
        """
        <style>
        :root {--line:#26344e; --panel:#121a2a; --muted:#9aa9bd;}
        .stApp {background: radial-gradient(circle at 88% -12%, #1b3c6d 0, transparent 32%), #090f1d; color:#f8fafc;}
        .block-container {max-width: 1440px; padding-top: 2rem; padding-bottom: 5rem;}
        [data-testid="stSidebar"] {background:linear-gradient(180deg,#101829,#0c1220); border-right:1px solid var(--line);}
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {background:#0a1020; border-color:#2a3955; border-radius:10px;}
        [data-testid="stChatMessage"] {border:1px solid #26344e; border-radius:15px; padding:.85rem 1rem; margin:.6rem 0; background:rgba(18,26,42,.9);}
        .stButton > button, [data-testid="stFormSubmitButton"] > button {border-radius:10px; min-height:2.5rem; border:1px solid #3b5682; background:linear-gradient(135deg,#1b3157,#182b4a); color:#fff; font-weight:650;}
        .stButton > button[kind="primary"] {background:linear-gradient(135deg,#b4495d,#7d243f); border-color:#e36a7a;}
        .stTextInput input, .stTextArea textarea {background:#0a1020 !important; border-color:#2b3b56 !important; border-radius:10px !important; color:#fff !important;}
        .console-hero {padding:1.65rem 1.8rem; border:1px solid rgba(121,167,255,.3); border-radius:20px; background:linear-gradient(120deg,rgba(28,55,100,.9),rgba(17,25,52,.92)); margin-bottom:1.35rem;}
        .console-hero .kicker {color:#93c4ff; letter-spacing:.14em; font-size:.7rem; font-weight:800;}.console-hero h1 {font-size:2.3rem; letter-spacing:-.055em; margin:.3rem 0 .35rem;}.console-hero p {color:#bfcbdd; margin:0;}
        .queue-label {font-size:.7rem; font-weight:800; letter-spacing:.12em; color:#8ebfff; margin:0 0 .55rem;}
        [data-testid="stMetric"] {background:rgba(18,26,42,.85); border:1px solid #26344e; padding:.8rem; border-radius:12px;}
        </style>
        <section class="console-hero"><div class="kicker">ACME CARE / OPERATIONS</div><h1>Human support console</h1><p>Review AI handoffs, communicate with customers, and close resolved requests.</p></section>
        """,
        unsafe_allow_html=True,
    )

    if not database_path().exists():
        st.error(f"Database not found: {database_path()}")
        st.code("python database/seed.py", language="bash")
        return

    st.markdown(CHAT_STYLE, unsafe_allow_html=True)
    st.markdown(navigation("agent"), unsafe_allow_html=True)
    with connect() as connection:
        snapshot = (
            tuple(connection.execute("SELECT COUNT(*), MAX(rowid) FROM messages").fetchone()),
            tuple(tuple(row) for row in connection.execute(
                "SELECT id, status, assigned_to FROM handoff_tickets ORDER BY id"
            )),
        )
    poll_inbox(snapshot)
    with st.sidebar:
        st.markdown("<div class='queue-label'>LIVE INBOX</div>", unsafe_allow_html=True)
        st.header("Queue filters")
        status = st.selectbox("Status", ("all", *TICKET_STATUSES))
        priority = st.selectbox("Priority", ("all", *PRIORITIES))
        if st.button("Refresh queue", use_container_width=True):
            st.rerun()
        st.divider()
        st.caption("Live inbox · updates automatically")

    try:
        tickets = list_tickets(status, priority)
    except sqlite3.Error as error:
        st.error(f"Could not read the support queue: {error}")
        return

    search = st.text_input("Search inbox", placeholder="Search customers, tickets, or messages…")
    if search:
        tickets = [row for row in tickets if search.lower() in " ".join(str(value or "") for value in row).lower()]
    left, right, details = st.columns((1, 2.4, 1), gap="medium")
    with left:
        st.markdown("<div class='queue-label'>PRIORITY QUEUE</div>", unsafe_allow_html=True)
        selected_id = render_ticket_list(tickets)
    if not selected_id:
        return

    ticket = get_ticket(selected_id)
    if ticket is None:
        st.warning("The selected ticket was removed. Refresh the queue.")
        return

    with details:
        st.subheader("Customer & order")
        st.caption(f"Ticket #{ticket['id'][:8]}")
        st.metric("Priority", ticket["priority"].title())
        st.metric("Status", ticket["status"].replace("_", " ").title())
        st.caption(f"Assigned to: {ticket['assigned_to'] or 'Unassigned'}")
        st.markdown(f"**Customer:** {ticket['full_name'] or 'Unknown'} {f'({ticket["email"]})' if ticket['email'] else ''}")
        st.markdown(f"**Handoff reason:** {ticket['reason']}")
        st.markdown("**AI summary**")
        st.info(ticket["ai_summary"])
        from services.support_service import SupportService
        service = SupportService(database_path())
        context = service.get_conversation_context(ticket["conversation_id"])
        st.caption(f"Order: {context['order_number'] or 'Not supplied'}")
        if context['order_number']:
            try:
                order = service.lookup_order(context['order_number'], context['email'] or None)
                if order:
                    st.markdown(f"**{order.status.title()}**")
                    st.caption(f"Estimated delivery: {order.estimated_delivery_date or 'Not available'}")
            except ValueError:
                st.caption("Order details need verification.")
    with right:
        render_transcript(ticket["conversation_id"])

        st.divider()
        st.subheader("Take action")
        specialist = st.text_input("Your name", value=ticket["assigned_to"] or "", key=f"specialist-{ticket['id']}")
        action_left, action_right = st.columns(2)
        with action_left:
            if st.button(
                "Assign to me",
                use_container_width=True,
                disabled=ticket["status"] in {"resolved", "waiting_customer"},
            ):
                try:
                    assign_ticket(ticket["id"], specialist)
                    st.success("Ticket assigned.")
                    st.rerun()
                except (ValueError, sqlite3.Error) as error:
                    st.error(str(error))
        with action_right:
            if st.button("Resolve ticket", type="primary", use_container_width=True, disabled=ticket["status"] == "resolved"):
                try:
                    resolve_ticket(ticket["id"], specialist)
                    st.success("Ticket resolved.")
                    st.rerun()
                except (ValueError, sqlite3.Error) as error:
                    st.error(str(error))

        waiting_for_customer = ticket["status"] == "waiting_customer"
        if waiting_for_customer:
            st.info("Waiting for the customer’s next message before the next human reply.")
        reply_disabled = ticket["status"] == "resolved" or waiting_for_customer
        with st.form(f"reply-{ticket['id']}", clear_on_submit=True):
            reply = st.text_area("Reply to customer", placeholder="Write a helpful, customer-ready response…", disabled=reply_disabled)
            sent = st.form_submit_button("Send reply", disabled=reply_disabled, use_container_width=True)
        if sent:
            try:
                post_reply(ticket["id"], reply, specialist)
                st.success("Reply sent to the customer conversation.")
                st.rerun()
            except (ValueError, sqlite3.Error) as error:
                st.error(str(error))


if __name__ == "__main__":
    main()
