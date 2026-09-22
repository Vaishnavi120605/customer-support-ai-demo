-- Customer Support AI Demo database schema.
-- SQLite foreign-key enforcement is connection-specific; enable it for every client.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    order_number TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL CHECK (status IN (
        'processing', 'packed', 'shipped', 'delivered', 'cancelled', 'returned', 'refunded'
    )),
    payment_status TEXT NOT NULL CHECK (payment_status IN ('paid', 'pending', 'refunded', 'disputed')),
    subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0),
    shipping_cents INTEGER NOT NULL CHECK (shipping_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    shipping_address TEXT NOT NULL,
    placed_at TEXT NOT NULL,
    estimated_delivery_date TEXT,
    delivered_at TEXT,
    cancellation_eligible INTEGER NOT NULL DEFAULT 0 CHECK (cancellation_eligible IN (0, 1)),
    return_eligible INTEGER NOT NULL DEFAULT 0 CHECK (return_eligible IN (0, 1)),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0)
);

CREATE TABLE IF NOT EXISTS order_events (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    location TEXT,
    details TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_articles (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES customers(id),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'awaiting_human', 'resolved', 'closed')),
    support_mode TEXT NOT NULL DEFAULT 'ai' CHECK (support_mode IN ('ai', 'human')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('customer', 'ai', 'human', 'system')),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS handoff_tickets (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL UNIQUE REFERENCES conversations(id),
    reason TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'waiting_customer', 'resolved')),
    assigned_to TEXT,
    ai_summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('customer', 'ai', 'human', 'system')),
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_order_events_order_id ON order_events(order_id, event_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_handoff_tickets_queue ON handoff_tickets(status, priority, created_at);
