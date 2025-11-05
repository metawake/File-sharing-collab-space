import os
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine
from app.models import User, File as FileModel
from app.config import settings
from sqlmodel import Session, select


def _setup_user_and_file(tmp_dir: str, email: str):
    os.makedirs(tmp_dir, exist_ok=True)
    settings.storage_dir = tmp_dir

    with Session(engine) as session:
        # Upsert user for test email
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing is None:
            user = User(email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
        else:
            user = existing
        user_email = email

        local_path = os.path.join(tmp_dir, "hello.txt")
        with open(local_path, "w", encoding="utf-8") as f:
            f.write("hello world")

        file = FileModel(
            user_id=user.id,  # type: ignore[arg-type]
            name="hello.txt",
            mime_type="text/plain",
            size_bytes=11,
            local_path=local_path,
        )
        session.add(file)
        session.commit()
        session.refresh(file)
        return user_email, file.id, local_path


def test_list_and_preview_and_delete(tmp_path):
    tmp_dir = str(tmp_path / "storage")
    email = f"files_{uuid4().hex}@example.com"
    user_email, file_id, local_path = _setup_user_and_file(tmp_dir, email)

    with TestClient(app) as client:
        # list
        r = client.get("/api/files", params={"email": user_email})
        assert r.status_code == 200
        data = r.json()
        names = [f["name"] for f in data["files"]]
        assert "hello.txt" in names

        # preview
        r2 = client.get(f"/api/files/{file_id}/preview", params={"email": user_email})
        assert r2.status_code == 200
        assert r2.content == b"hello world"
        assert r2.headers["content-type"].startswith("text/plain")

        # delete
        r3 = client.delete(f"/api/files/{file_id}", params={"email": user_email})
        assert r3.status_code == 200
        assert r3.json()["deleted"] is True
        assert not os.path.exists(local_path)

