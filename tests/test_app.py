import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "farmtrack9")
os.environ["TWILIO_ACCOUNT_SID"] = ""
os.environ["TWILIO_AUTH_TOKEN"] = ""
os.environ["TWILIO_PHONE_NUMBER"] = ""
os.environ["DEMO_RECIPIENT_NUMBER"] = ""
os.environ["DEMO_RECIPIENT_NUMBERS"] = ""

from app import app


def test_home_and_seeded_batch():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"TOM-001" in response.data


def test_tracking_page_and_qr():
    client = app.test_client()
    page = client.get("/track/TOM-001")
    qr = client.get("/qr/TOM-001.png")
    assert page.status_code == 200
    assert b"Journey timeline" in page.data
    assert b"FRESHNESS SCORE" in page.data
    assert b"Bangalore Fruit &amp; Vegetable APMC" in page.data
    assert qr.status_code == 200
    assert qr.content_type == "image/png"


def test_bengaluru_market_directory():
    client = app.test_client()
    response = client.get("/markets")
    assert response.status_code == 200
    assert b"Bangalore APMC, Yeshwanthpur" in response.data
    assert b"Doddaballapur APMC" in response.data
    assert b"K. R. Market" in response.data


def test_presenter_requires_login():
    client = app.test_client()
    response = client.get("/admin")
    assert response.status_code == 302
    assert "/login" in response.location


def test_login_and_demo_notification():
    client = app.test_client()
    login = client.post("/login", data={"password": "farmtrack9"}, follow_redirects=True)
    assert login.status_code == 200
    assert b"Journey control centre" in login.data
    os.environ["DEMO_RECIPIENT_NUMBER"] = "+919999999999"
    notify = client.post("/admin/batches/1/notify", data={"recipient": "+919999999999"}, follow_redirects=True)
    assert notify.status_code == 200
    assert b"Demo notification saved" in notify.data
    os.environ["DEMO_RECIPIENT_NUMBER"] = ""

