"""OnionRANK – a just-for-fun leaderboard of .onion domains ranked by BTC paid."""
import hmac
import json
import os
import re
import secrets
import time

from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

from . import badge, db
from .payments import PaymentError, make_provider

# v3 onion address: 56 base32 chars (a-z, 2-7) ending in 'd' (version 3)
ONION_RE = re.compile(r"^[a-z2-7]{55}d\.onion$")


def normalize_onion(raw):
    s = (raw or "").strip().lower()
    s = re.sub(r"^https?://", "", s).split("/")[0]
    if "." in s and not s.endswith(".onion"):
        return None
    if not s.endswith(".onion"):
        s += ".onion"
    # strip subdomains: foo.<addr>.onion -> <addr>.onion
    parts = s.split(".")
    s = ".".join(parts[-2:])
    return s if ONION_RE.match(s) else None


def fmt_sats(sats):
    return f"{sats:,}".replace(",", " ")


def fmt_btc(sats):
    return f"{sats / 1e8:.8f}"


def fmt_short(ts):
    return time.strftime("%m-%d %H:%M", time.gmtime(ts)) if ts else "--"


def fmt_time(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts)) + " UTC" if ts else "--"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("DATABASE", os.path.join(app.instance_path, "onionrank.sqlite")),
        PAYMENT_PROVIDER=os.environ.get("PAYMENT_PROVIDER", "demo"),
        BTCPAY_URL=os.environ.get("BTCPAY_URL", ""),
        BTCPAY_STORE_ID=os.environ.get("BTCPAY_STORE_ID", ""),
        BTCPAY_API_KEY=os.environ.get("BTCPAY_API_KEY", ""),
        BTCPAY_WEBHOOK_SECRET=os.environ.get("BTCPAY_WEBHOOK_SECRET", ""),
        BTCPAY_PROXY=os.environ.get("BTCPAY_PROXY"),
        BTCPAY_HOST_HEADER=os.environ.get("BTCPAY_HOST_HEADER"),
        BTCPAY_PUBLIC_URL=os.environ.get("BTCPAY_PUBLIC_URL"),
        ADMIN_TOKEN=os.environ.get("ADMIN_TOKEN", ""),
        SITE_URL=os.environ.get("SITE_URL", ""),  # your own .onion URL, for redirects
        MIN_SATS=int(os.environ.get("MIN_SATS", "1000")),
        MAX_SATS=int(os.environ.get("MAX_SATS", "100000000")),
        MAX_PENDING_SUBMISSIONS=int(os.environ.get("MAX_PENDING_SUBMISSIONS", "300")),
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    provider = make_provider(app.config)
    app.extensions["payments"] = provider
    app.jinja_env.filters.update(sats=fmt_sats, btc=fmt_btc, when=fmt_time, short=fmt_short)

    @app.context_processor
    def inject():
        return {
            "provider_name": provider.name,
            "min_sats": app.config["MIN_SATS"],
            "endpoint": request.endpoint,
        }

    @app.after_request
    def security_headers(resp):
        # Tor-friendly: no third-party content, no scripts, no referrers.
        resp.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self' https: http:; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    # ------------------------------------------------------------------ public

    @app.get("/")
    def index():
        period = request.args.get("p", "all")
        since = {"30d": time.time() - 30 * 86400, "7d": time.time() - 7 * 86400}.get(period)
        return render_template(
            "index.html",
            rows=db.ranking(since=since),
            period=period,
            stats=db.global_stats(),
            recent=db.recent_payments(),
        )

    def visible_domain(onion):
        d = db.domain_by_onion(onion)
        if not d or not db.is_visible(d["id"]):
            abort(404)
        return d

    def site_base():
        return app.config["SITE_URL"].rstrip("/") or request.host_url.rstrip("/")

    @app.get("/d/<onion>")
    def domain(onion):
        d = visible_domain(onion)
        return render_template(
            "domain.html",
            d=d,
            stats=db.domain_stats(d["id"]),
            rank=db.domain_rank(d["id"]),
            messages=db.recent_messages(d["id"]),
            base=site_base(),
        )

    # ------------------------------------------------------------------ badges

    @app.get("/badge/<onion>.png")
    def badge_png(onion):
        d = visible_domain(onion)
        resp = Response(badge.png(db.domain_rank(d["id"])), mimetype="image/png")
        resp.headers["Cache-Control"] = "public, max-age=600"
        return resp

    @app.get("/badge/<onion>.svg")
    def badge_svg(onion):
        d = visible_domain(onion)
        resp = Response(badge.svg(db.domain_rank(d["id"])), mimetype="image/svg+xml")
        resp.headers["Cache-Control"] = "public, max-age=600"
        return resp

    # ------------------------------------------------------------ free listing

    def make_challenge():
        a, b = secrets.randbelow(9) + 1, secrets.randbelow(9) + 1
        ts = str(int(time.time()))
        return {"q": f"{a} + {b}", "ts": ts, "sig": _sig(a + b, ts)}

    def _sig(answer, ts):
        key = app.config["SECRET_KEY"].encode()
        return hmac.new(key, f"{answer}:{ts}".encode(), "sha256").hexdigest()

    def check_challenge(form):
        try:
            answer, ts = int(form.get("answer", "")), int(form.get("ts", ""))
        except ValueError:
            return False
        if not 3 <= time.time() - ts <= 3600:  # too fast (bot) or too old
            return False
        return hmac.compare_digest(_sig(answer, str(ts)), form.get("sig", ""))

    @app.route("/submit", methods=["GET", "POST"])
    def submit():
        form = request.form
        if request.method == "GET":
            return render_template("submit.html", form={}, ch=make_challenge())

        onion = normalize_onion(form.get("onion"))
        title = (form.get("title") or "").strip()[:80]
        description = (form.get("description") or "").strip()[:280]
        errors = []
        if not onion:
            errors.append("Invalid address – enter a v3 .onion address (56 characters).")
        if not title:
            errors.append("Please enter a title.")
        if not check_challenge(form):
            errors.append("Wrong answer to the anti-spam question, please try again.")
        existing = db.domain_by_onion(onion) if onion else None
        if existing:
            if existing["banned"]:
                errors.append("This domain has been removed from the leaderboard.")
            elif db.is_visible(existing["id"]):
                errors.append("This domain is already listed.")
            else:
                errors.append("This domain is already waiting for approval.")
        if not errors and db.count_pending_submissions() >= app.config["MAX_PENDING_SUBMISSIONS"]:
            errors.append("The review queue is full right now, please try again later.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("submit.html", form=form, ch=make_challenge()), 400

        db.upsert_domain(onion, title, description)
        flash("Submitted! Your domain will appear once an admin approves it.", "ok")
        return redirect(url_for("submit"))

    @app.route("/boost", methods=["GET", "POST"])
    def boost():
        form = request.form if request.method == "POST" else request.args
        if request.method == "GET":
            return render_template("boost.html", form=form)

        onion = normalize_onion(form.get("onion"))
        title = (form.get("title") or "").strip()[:80]
        description = (form.get("description") or "").strip()[:280]
        message = (form.get("message") or "").strip()[:140]
        try:
            amount = int(form.get("amount_sats", "0"))
        except ValueError:
            amount = 0

        errors = []
        if not onion:
            errors.append("Invalid address – enter a v3 .onion address (56 characters).")
        if amount < app.config["MIN_SATS"] or amount > app.config["MAX_SATS"]:
            errors.append(
                f"Amount must be between {fmt_sats(app.config['MIN_SATS'])} and "
                f"{fmt_sats(app.config['MAX_SATS'])} sats."
            )
        existing = db.domain_by_onion(onion) if onion else None
        if existing and existing["banned"]:
            errors.append("This domain has been removed from the leaderboard.")
        if not existing and not title:
            errors.append("A new domain needs a title.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("boost.html", form=form), 400

        d = existing or db.upsert_domain(onion, title, description)
        order_id = secrets.token_urlsafe(12)
        db.create_order(order_id, d["id"], amount, message)

        base = app.config["SITE_URL"].rstrip("/") or request.host_url.rstrip("/")
        try:
            inv = provider.create_invoice(
                order_id, amount, f"OnionRANK boost {onion}", f"{base}/order/{order_id}"
            )
        except PaymentError as e:
            app.logger.error("invoice failed: %s", e)
            db.mark_order(order_id, "expired")
            flash("The payment gateway is unavailable right now, please try again later.", "error")
            return render_template("boost.html", form=form), 502
        db.set_order_invoice(order_id, inv["invoice_id"], inv["checkout_url"])
        if inv["checkout_url"]:
            return redirect(inv["checkout_url"])
        return redirect(url_for("order", order_id=order_id))

    @app.get("/order/<order_id>")
    def order(order_id):
        o = db.get_order(order_id)
        if not o:
            abort(404)
        # Poll the provider as a fallback in case the webhook got lost.
        if o["status"] == "pending" and o["invoice_id"]:
            try:
                st = provider.invoice_status(o["invoice_id"])
            except PaymentError:
                st = None
            if st in ("paid", "expired"):
                db.mark_order(order_id, st)
                o = db.get_order(order_id)
        return render_template("order.html", o=o)

    @app.post("/order/<order_id>/demo-pay")
    def demo_pay(order_id):
        if provider.name != "demo":
            abort(404)
        if not db.get_order(order_id):
            abort(404)
        db.mark_order(order_id, "paid")
        flash("Demo payment credited.", "ok")
        return redirect(url_for("order", order_id=order_id))

    @app.get("/faq")
    def faq():
        return render_template("faq.html")

    # ----------------------------------------------------------------- webhook

    @app.post("/webhook/btcpay")
    def btcpay_webhook():
        body = request.get_data()
        if not provider.verify_webhook(body, request.headers.get("BTCPay-Sig")):
            abort(401)
        try:
            event = json.loads(body)
        except ValueError:
            abort(400)
        o = db.get_order_by_invoice(event.get("invoiceId", ""))
        if not o:
            return "", 204
        # Never trust the event body alone – ask BTCPay for the authoritative status.
        if event.get("type") in ("InvoiceSettled", "InvoiceExpired", "InvoiceInvalid"):
            st = provider.invoice_status(o["invoice_id"])
            if st in ("paid", "expired"):
                db.mark_order(o["id"], st)
        return "", 204

    # ------------------------------------------------------------------- admin

    def require_admin():
        token = app.config["ADMIN_TOKEN"]
        given = request.args.get("t") or request.form.get("t") or ""
        if not token or not hmac.compare_digest(token, given):
            abort(404)
        return token

    @app.get("/admin")
    def admin():
        t = require_admin()
        return render_template(
            "admin.html",
            t=t,
            domains=db.all_domains(),
            pending=db.pending_orders(),
            submissions=db.pending_submissions(),
        )

    @app.post("/admin/approve")
    def admin_approve():
        t = require_admin()
        onion = request.form["onion"]
        if request.form.get("action") == "reject":
            db.set_banned(onion, True)
        else:
            db.set_approved(onion, True)
        return redirect(url_for("admin", t=t))

    @app.post("/admin/ban")
    def admin_ban():
        t = require_admin()
        db.set_banned(request.form["onion"], request.form.get("banned") == "1")
        return redirect(url_for("admin", t=t))

    @app.post("/admin/mark")
    def admin_mark():
        t = require_admin()
        status = request.form.get("status")
        if status in ("paid", "expired"):
            db.mark_order(request.form["order_id"], status)
        return redirect(url_for("admin", t=t))

    @app.cli.command("reconcile")
    def reconcile():
        """Ask the payment provider about pending orders (webhook fallback)."""
        checked = changed = 0
        for o in db.pending_invoices():
            checked += 1
            try:
                st = provider.invoice_status(o["invoice_id"])
            except PaymentError as e:
                print(f"{o['id']}: {e}")
                continue
            if st in ("paid", "expired"):
                db.mark_order(o["id"], st)
                changed += 1
                print(f"{o['id']}: {st}")
        print(f"checked {checked}, updated {changed}")

    return app
