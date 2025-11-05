from fastapi.testclient import TestClient
from app.main import app


def test_logout_clears_session():
    with TestClient(app) as client:
        r = client.post("/auth/logout")
        assert r.status_code == 200
        assert r.json().get("ok") is True

