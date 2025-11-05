import os
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from app.models import User, OAuthToken, File
from app.config import settings
from sqlmodel import Session, select


def _setup_user_with_token(email: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            user = User(email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
        token = session.exec(select(OAuthToken).where(OAuthToken.user_id == user.id)).first()
        if not token:
            token = OAuthToken(user_id=user.id, provider="google", access_token="old-access", refresh_token="refresh-token")
            session.add(token)
            session.commit()
            session.refresh(token)
        return user, token


def test_import_success_and_duplicate(tmp_path, monkeypatch):
    settings.storage_dir = str(tmp_path / "storage")
    email = f"import_{uuid4().hex}@example.com"
    user, token = _setup_user_with_token(email)

    # Fake Google responses: metadata then content
    from httpx import AsyncClient

    async def fake_get(self, url, headers=None, **kw):
        class R:
            def __init__(self, code, data=None, content=b"", headers=None):
                self.status_code = code
                self._data = data
                self.content = content
                self.headers = headers or {}
            def json(self):
                return self._data
            @property
            def text(self):
                return ""
        if url.endswith("?fields=id,name,mimeType,size,md5Checksum"):
            return R(200, {"id": "fid1", "name": "doc.txt", "mimeType": "text/plain", "size": "11"})
        if url.endswith("?alt=media"):
            return R(200, content=b"hello world", headers={"Content-Type": "text/plain"})
        raise AssertionError("unexpected GET url: " + url)

    monkeypatch.setattr(AsyncClient, "get", fake_get)

    with TestClient(app) as client:
        r = client.post("/api/import", json={"email": email, "drive_file_ids": ["fid1"]})
        assert r.status_code == 200
        res = r.json()
        assert res["results"][0]["status"] == "imported"

        # duplicate call should dedupe
        r2 = client.post("/api/import", json={"email": email, "drive_file_ids": ["fid1"]})
        assert r2.status_code == 200
        res2 = r2.json()
        assert res2["results"][0]["status"] == "duplicate"

    # file persisted
    with Session(engine) as session:
        u = session.exec(select(User).where(User.email == email)).first()
        assert u is not None
        files = session.exec(select(File).where(File.user_id == u.id)).all()
        assert len(files) == 1
        assert os.path.exists(files[0].local_path)


def test_import_refresh_on_401(tmp_path, monkeypatch):
    settings.storage_dir = str(tmp_path / "storage")
    email = f"import_refresh_{uuid4().hex}@example.com"
    user, token = _setup_user_with_token(email)

    # Fake Google responses: first 401 for metadata and download, then after refresh, success
    from httpx import AsyncClient
    calls = {"post": 0, "get": 0}

    async def fake_post(self, url, data=None, **kw):
        class R:
            def __init__(self, code, data):
                self.status_code = code
                self._data = data
            def json(self):
                return self._data
        if "oauth2.googleapis.com/token" in url:
            calls["post"] += 1
            return R(200, {"access_token": "new-access"})
        raise AssertionError("unexpected POST url: " + url)

    async def fake_get(self, url, headers=None, **kw):
        class R:
            def __init__(self, code, data=None, content=b"", headers=None):
                self.status_code = code
                self._data = data
                self.content = content
                self.headers = headers or {}
            def json(self):
                return self._data
            @property
            def text(self):
                return ""
        calls["get"] += 1
        if calls["get"] == 1:
            return R(401)
        if url.endswith("?fields=id,name,mimeType,size,md5Checksum"):
            return R(200, {"id": "fid2", "name": "file.bin", "mimeType": "application/octet-stream", "size": "3"})
        if url.endswith("?alt=media"):
            return R(200, content=b"xyz", headers={"Content-Type": "application/octet-stream"})
        raise AssertionError("unexpected GET url: " + url)

    monkeypatch.setattr(AsyncClient, "post", fake_post)
    monkeypatch.setattr(AsyncClient, "get", fake_get)

    with TestClient(app) as client:
        r = client.post("/api/import", json={"email": email, "drive_file_ids": ["fid2"]})
        assert r.status_code == 200
        res = r.json()
        assert res["results"][0]["status"] == "imported"

    # token updated
    with Session(engine) as session:
        u = session.exec(select(User).where(User.email == email)).first()
        assert u is not None
        t = session.exec(select(OAuthToken).where(OAuthToken.user_id == u.id)).first()
        assert t is not None
        assert t.access_token == "new-access"

