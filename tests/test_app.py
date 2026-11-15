import hashlib, hmac, json
import pytest
from onionrank import create_app, normalize_onion
from onionrank.payments import BTCPayProvider

A = "a" * 55 + "d.onion"
B = "b" * 55 + "d.onion"


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.db"), "ADMIN_TOKEN": "secret"})
    return app.test_client()


def boost(c, onion, sats, title="X"):
    r = c.post("/boost", data={"onion": onion, "title": title, "amount_sats": sats})
    assert r.status_code == 302
    oid = r.headers["Location"].rsplit("/", 1)[-1]
    c.post(f"/order/{oid}/demo-pay")
    return oid


def test_normalize():
    assert normalize_onion("http://" + A.upper() + "/x") == A
    assert normalize_onion("www." + A) == A
    assert normalize_onion(A[:-6]) == A
    assert normalize_onion("example.com") is None
    assert normalize_onion("abc.onion") is None


def test_ranking_order(client):
    boost(client, A, 5000, "Alfa")
    boost(client, B, 8000, "Beta")
    html = client.get("/").get_data(as_text=True)
    assert html.index("Beta") < html.index("Alfa")
    boost(client, A, 5000)
    html = client.get("/").get_data(as_text=True)
    assert html.index("Alfa") < html.index("Beta")


def test_amounts_not_public(client):
    boost(client, A, 123457, "Alfa")
    for url in ("/", f"/d/{A}"):
        html = client.get(url).get_data(as_text=True)
        assert "123 457" not in html and "123457" not in html and "0.00123457" not in html


def test_pending_not_counted(client):
    client.post("/boost", data={"onion": A, "title": "Alfa", "amount_sats": 5000})
    assert "Alfa" not in client.get("/").get_data(as_text=True)


def test_validation(client):
    assert client.post("/boost", data={"onion": "nope", "title": "x", "amount_sats": 5000}).status_code == 400
    assert client.post("/boost", data={"onion": A, "title": "x", "amount_sats": 1}).status_code == 400
    assert client.post("/boost", data={"onion": A, "amount_sats": 5000}).status_code == 400


def test_ban(client):
    boost(client, A, 5000, "Alfa")
    assert client.get("/admin").status_code == 404
    client.post("/admin/ban", data={"t": "secret", "onion": A, "banned": "1"})
    assert "Alfa" not in client.get("/").get_data(as_text=True)
    assert client.get(f"/d/{A}").status_code == 404


def test_xss_escaped(client):
    boost(client, A, 5000, "<script>x</script>")
    assert "<script>x" not in client.get("/").get_data(as_text=True)


def test_btcpay_local_mode(monkeypatch):
    seen = {}

    class R:
        status_code = 200
        def json(self):
            return {"id": "inv1", "checkoutLink": "http://btcpay.local/i/inv1?x=1"}

    def fake(method, url, headers=None, proxies=None, **kw):
        seen.update(url=url, headers=headers, proxies=proxies)
        return R()

    monkeypatch.setattr("onionrank.payments.requests.request", fake)
    p = BTCPayProvider("http://127.0.0.1:8081", "S", "K", "W",
                       host_header="btcpay.local", public_url="http://" + "p" * 56 + ".onion/")
    inv = p.create_invoice("o1", 10000, "d", "http://x")
    assert seen["url"] == "http://127.0.0.1:8081/api/v1/stores/S/invoices"
    assert seen["headers"]["Host"] == "btcpay.local" and seen["proxies"] is None
    assert inv["checkout_url"] == "http://" + "p" * 56 + ".onion/i/inv1?x=1"


def test_reconcile(tmp_path, monkeypatch):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "r.db")})
    c = app.test_client()
    c.post("/boost", data={"onion": A, "title": "Alfa", "amount_sats": 5000})
    provider = app.extensions["payments"]
    monkeypatch.setattr(provider, "invoice_status", lambda inv: "paid")
    out = app.test_cli_runner().invoke(args=["reconcile"]).output
    assert "updated 1" in out
    assert "Alfa" in c.get("/").get_data(as_text=True)


def test_btcpay_signature():
    p = BTCPayProvider("https://x", "s", "k", "whsec")
    body = b'{"a":1}'
    sig = "sha256=" + hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert p.verify_webhook(body, sig)
    assert not p.verify_webhook(body, "sha256=00")
