"""Bitcoin payment providers.

* ``btcpay`` – self-hosted BTCPay Server (Greenfield API). Recommended for
  production: it generates a fresh address per invoice, watches the chain and
  notifies us through a signed webhook. It runs happily behind Tor.
* ``demo``   – no real payments; an order can be confirmed with a button.
  Only for local development.
"""
import hashlib
import hmac

import requests


class PaymentError(Exception):
    pass


class DemoProvider:
    name = "demo"

    def create_invoice(self, order_id, amount_sats, description, redirect_url):
        return {"invoice_id": f"demo-{order_id}", "checkout_url": None}

    def invoice_status(self, invoice_id):
        return None

    def verify_webhook(self, body, signature_header):
        return False


class BTCPayProvider:
    name = "btcpay"

    def __init__(self, url, store_id, api_key, webhook_secret, proxy=None, timeout=30):
        self.url = url.rstrip("/")
        self.store_id = store_id
        self.api_key = api_key
        self.webhook_secret = webhook_secret.encode() if webhook_secret else b""
        self.timeout = timeout
        # e.g. socks5h://127.0.0.1:9050 when BTCPay is itself an onion service
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    def _req(self, method, path, **kw):
        try:
            r = requests.request(
                method,
                f"{self.url}/api/v1/stores/{self.store_id}{path}",
                headers={"Authorization": f"token {self.api_key}"},
                proxies=self.proxies,
                timeout=self.timeout,
                **kw,
            )
        except requests.RequestException as e:
            raise PaymentError(f"BTCPay nedostupný: {e}") from e
        if r.status_code >= 400:
            raise PaymentError(f"BTCPay chyba {r.status_code}: {r.text[:200]}")
        return r.json()

    def create_invoice(self, order_id, amount_sats, description, redirect_url):
        data = self._req(
            "POST",
            "/invoices",
            json={
                "amount": f"{amount_sats / 1e8:.8f}",
                "currency": "BTC",
                "metadata": {"orderId": order_id, "itemDesc": description},
                "checkout": {"redirectURL": redirect_url, "redirectAutomatically": True},
            },
        )
        return {"invoice_id": data["id"], "checkout_url": data.get("checkoutLink")}

    def invoice_status(self, invoice_id):
        """Return 'paid', 'expired' or 'pending'."""
        status = self._req("GET", f"/invoices/{invoice_id}").get("status")
        if status == "Settled":
            return "paid"
        if status in ("Expired", "Invalid"):
            return "expired"
        return "pending"

    def verify_webhook(self, body, signature_header):
        if not self.webhook_secret or not signature_header:
            return False
        expected = "sha256=" + hmac.new(self.webhook_secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)


def make_provider(cfg):
    if cfg.get("PAYMENT_PROVIDER") == "btcpay":
        return BTCPayProvider(
            cfg["BTCPAY_URL"],
            cfg["BTCPAY_STORE_ID"],
            cfg["BTCPAY_API_KEY"],
            cfg["BTCPAY_WEBHOOK_SECRET"],
            proxy=cfg.get("BTCPAY_PROXY"),
        )
    return DemoProvider()
