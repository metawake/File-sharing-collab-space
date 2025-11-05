from fastapi.testclient import TestClient
from app.main import app


def test_google_login_requires_config():
    with TestClient(app, follow_redirects=False) as client:
        resp = client.get("/auth/google/login")
    if resp.status_code == 500:
        assert resp.json()["detail"] == "Google OAuth is not configured"
    else:
        assert resp.status_code in (302, 307)
        assert "accounts.google.com" in resp.headers.get("location", "")
