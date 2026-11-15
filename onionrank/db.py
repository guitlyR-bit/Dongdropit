"""SQLite storage for OnionRANK."""
import sqlite3
import time

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    onion       TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    banned      INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id           TEXT PRIMARY KEY,           -- random public order id
    domain_id    INTEGER NOT NULL REFERENCES domains(id),
    amount_sats  INTEGER NOT NULL,
    message      TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | paid | expired
    invoice_id   TEXT,
    checkout_url TEXT,
    created_at   INTEGER NOT NULL,
    paid_at      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_orders_domain ON orders(domain_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_invoice ON orders(invoice_id);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    get_db().executescript(SCHEMA)


def now():
    return int(time.time())


def ranking(since=None, limit=100):
    """Return non-banned domains ordered by sats paid (optionally since a timestamp)."""
    params = []
    paid_filter = "o.status = 'paid'"
    if since is not None:
        paid_filter += " AND o.paid_at >= ?"
        params.append(since)
    params.append(limit)
    return get_db().execute(
        f"""
        SELECT d.id, d.onion, d.title, d.description,
               COALESCE(SUM(o.amount_sats), 0) AS total_sats,
               COUNT(o.id) AS payments,
               MAX(o.paid_at) AS last_paid
        FROM domains d
        JOIN orders o ON o.domain_id = d.id AND {paid_filter}
        WHERE d.banned = 0
        GROUP BY d.id
        ORDER BY total_sats DESC, last_paid ASC
        LIMIT ?
        """,
        params,
    ).fetchall()


def domain_by_onion(onion):
    return get_db().execute("SELECT * FROM domains WHERE onion = ?", (onion,)).fetchone()


def domain_stats(domain_id):
    return get_db().execute(
        """SELECT COALESCE(SUM(amount_sats),0) AS total_sats, COUNT(*) AS payments,
                  MAX(paid_at) AS last_paid
           FROM orders WHERE domain_id = ? AND status = 'paid'""",
        (domain_id,),
    ).fetchone()


def domain_rank(domain_id):
    """1-based all-time position of a domain, or None if unranked."""
    for i, row in enumerate(ranking(limit=100000), start=1):
        if row["id"] == domain_id:
            return i
    return None


def recent_messages(domain_id, limit=10):
    return get_db().execute(
        """SELECT amount_sats, message, paid_at FROM orders
           WHERE domain_id = ? AND status = 'paid' AND message != ''
           ORDER BY paid_at DESC LIMIT ?""",
        (domain_id, limit),
    ).fetchall()


def upsert_domain(onion, title, description):
    db = get_db()
    row = domain_by_onion(onion)
    if row:
        return row
    db.execute(
        "INSERT INTO domains (onion, title, description, created_at) VALUES (?,?,?,?)",
        (onion, title, description, now()),
    )
    db.commit()
    return domain_by_onion(onion)


def create_order(order_id, domain_id, amount_sats, message):
    db = get_db()
    db.execute(
        """INSERT INTO orders (id, domain_id, amount_sats, message, created_at)
           VALUES (?,?,?,?,?)""",
        (order_id, domain_id, amount_sats, message, now()),
    )
    db.commit()


def set_order_invoice(order_id, invoice_id, checkout_url):
    db = get_db()
    db.execute(
        "UPDATE orders SET invoice_id = ?, checkout_url = ? WHERE id = ?",
        (invoice_id, checkout_url, order_id),
    )
    db.commit()


def get_order(order_id):
    return get_db().execute(
        """SELECT o.*, d.onion, d.title FROM orders o
           JOIN domains d ON d.id = o.domain_id WHERE o.id = ?""",
        (order_id,),
    ).fetchone()


def get_order_by_invoice(invoice_id):
    return get_db().execute("SELECT * FROM orders WHERE invoice_id = ?", (invoice_id,)).fetchone()


def mark_order(order_id, status):
    db = get_db()
    if status == "paid":
        # Only credit once.
        db.execute(
            "UPDATE orders SET status='paid', paid_at=? WHERE id=? AND status!='paid'",
            (now(), order_id),
        )
    else:
        db.execute("UPDATE orders SET status=? WHERE id=? AND status='pending'", (status, order_id))
    db.commit()


def set_banned(onion, banned):
    db = get_db()
    db.execute("UPDATE domains SET banned=? WHERE onion=?", (1 if banned else 0, onion))
    db.commit()


def all_domains():
    return get_db().execute(
        """SELECT d.*, COALESCE(SUM(CASE WHEN o.status='paid' THEN o.amount_sats END),0) AS total_sats
           FROM domains d LEFT JOIN orders o ON o.domain_id=d.id
           GROUP BY d.id ORDER BY d.created_at DESC"""
    ).fetchall()


def pending_invoices(max_age_days=7):
    """Pending orders with an invoice, young enough to still get paid."""
    return get_db().execute(
        """SELECT id, invoice_id FROM orders
           WHERE status='pending' AND invoice_id IS NOT NULL AND created_at >= ?""",
        (now() - max_age_days * 86400,),
    ).fetchall()


def pending_orders():
    return get_db().execute(
        """SELECT o.*, d.onion FROM orders o JOIN domains d ON d.id=o.domain_id
           WHERE o.status='pending' ORDER BY o.created_at DESC LIMIT 200"""
    ).fetchall()


def global_stats():
    return get_db().execute(
        """SELECT COALESCE(SUM(o.amount_sats),0) AS total_sats, COUNT(o.id) AS payments,
                  COUNT(DISTINCT o.domain_id) AS domains
           FROM orders o JOIN domains d ON d.id=o.domain_id
           WHERE o.status='paid' AND d.banned=0"""
    ).fetchone()


def recent_payments(limit=6):
    return get_db().execute(
        """SELECT o.amount_sats, o.paid_at, d.onion, d.title FROM orders o
           JOIN domains d ON d.id=o.domain_id
           WHERE o.status='paid' AND d.banned=0 ORDER BY o.paid_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
