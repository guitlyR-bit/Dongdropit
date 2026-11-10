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


def test_btcpay_signature():
    p = BTCPayProvider("https://x", "s", "k", "whsec")
    body = b'{"a":1}'
    sig = "sha256=" + hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert p.verify_webhook(body, sig)
    assert not p.verify_webhook(body, "sha256=00")
