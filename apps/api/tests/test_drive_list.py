from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from app.models import User, OAuthToken
from sqlmodel import Session, select


def _setup_user_with_token(email: str):
  with Session(engine) as session:
    u = session.exec(select(User).where(User.email == email)).first()
    if not u:
      u = User(email=email)
      session.add(u)
      session.commit()
      session.refresh(u)
    t = session.exec(select(OAuthToken).where(OAuthToken.user_id == u.id)).first()
    if not t:
      t = OAuthToken(user_id=u.id, provider="google", access_token="old", refresh_token="refresh")
      session.add(t)
      session.commit()
    return u


def test_drive_files_lists(monkeypatch):
  email = f"list_{uuid4().hex}@example.com"
  _setup_user_with_token(email)

  from httpx import AsyncClient

  async def fake_get(self, url, headers=None, **kw):
    class R:
      def __init__(self):
        self.status_code = 200
      def json(self):
        return {"files": [{"id": "fid", "name": "doc.txt", "mimeType": "text/plain", "size": "10"}], "nextPageToken": None}
    return R()

  monkeypatch.setattr(AsyncClient, "get", fake_get)

  with TestClient(app) as client:
    r = client.get("/api/drive/files", params={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert "files" in body and len(body["files"]) == 1

