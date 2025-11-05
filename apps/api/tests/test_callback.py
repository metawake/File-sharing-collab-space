from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.db import engine
from app.models import User, OAuthToken
from sqlmodel import Session, select


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


def test_callback_persists_user_and_token(monkeypatch):
    # Configure settings dynamically for test
    settings.google_client_id = "test-client-id"
    settings.google_client_secret = "test-client-secret"
    settings.google_redirect_uri = "http://localhost:8000/auth/google/callback"

    # Mock HTTP calls: token exchange and userinfo
    async def _fake_post(self, url, data=None, **kwargs):  # type: ignore[no-redef]
        assert "oauth2.googleapis.com/token" in url
        return _FakeResponse(
            200,
            {
                "access_token": "fake-access",
                "refresh_token": "fake-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "openid email profile",
            },
        )

    async def _fake_get(self, url, headers=None, **kwargs):  # type: ignore[no-redef]
        assert "openidconnect.googleapis.com" in url
        assert headers and headers.get("Authorization") == "Bearer fake-access"
        return _FakeResponse(200, {"email": "test@example.com"})

    from httpx import AsyncClient

    monkeypatch.setattr(AsyncClient, "post", _fake_post)
    monkeypatch.setattr(AsyncClient, "get", _fake_get)

    # Exercise callback
    with TestClient(app, follow_redirects=False) as client:
        resp = client.get("/auth/google/callback", params={"code": "abc"})
    assert resp.status_code in (302, 307)
    loc = resp.headers.get("location")
    assert loc is not None
    assert loc.startswith("http://localhost:3000/?connected=1")

    # Validate DB state
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == "test@example.com")
        ).first()
        assert user is not None
        token = session.exec(
            select(OAuthToken).where(OAuthToken.user_id == user.id)
        ).first()
        assert token is not None
        assert token.access_token == "fake-access"
        assert token.refresh_token == "fake-refresh"
        assert token.provider == "google"
