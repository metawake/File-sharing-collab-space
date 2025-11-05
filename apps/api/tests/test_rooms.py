from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.db import engine
from apps.api.app.models import User, Room, Membership, File as FileModel
from sqlmodel import Session, select
import os
from uuid import uuid4


def test_rooms_membership_and_rbac(tmp_path):
    storage_dir = tmp_path / "storage"
    os.makedirs(storage_dir, exist_ok=True)

    owner_email = f"owner_{uuid4().hex}@example.com"
    viewer_email = f"viewer_{uuid4().hex}@example.com"

    # Create room as owner via API
    with TestClient(app) as client:
        r = client.post("/api/rooms", params={"email": owner_email}, json={"name": "Case A"})
        assert r.status_code == 200
        room_id = r.json()["id"]

        # Add viewer member
        r2 = client.post(f"/api/rooms/{room_id}/members", params={"email": owner_email}, json={"email": viewer_email, "role": "viewer"})
        assert r2.status_code == 200

        # Seed a file for owner (simulate an imported file)
        file_content = b"hello legal world"
        file_path = storage_dir / "doc.txt"
        with open(file_path, "wb") as f:
            f.write(file_content)

        with Session(engine) as session:
            # Ensure users exist
            owner = session.exec(select(User).where(User.email == owner_email)).first()
            if not owner:
                owner = User(email=owner_email)
                session.add(owner)
                session.commit()
                session.refresh(owner)
            frow = FileModel(
                user_id=owner.id,  # type: ignore[arg-type]
                drive_file_id=None,
                name="doc.txt",
                mime_type="text/plain",
                size_bytes=len(file_content),
                local_path=str(file_path),
                sha256=None,
            )
            session.add(frow)
            session.commit()
            session.refresh(frow)
            file_id = frow.id

        # Link file into room
        r3 = client.post(f"/api/rooms/{room_id}/files", params={"email": owner_email}, json={"file_id": file_id})
        assert r3.status_code == 200
        assert r3.json()["linked"] is True

        # Viewer can list files in room
        r4 = client.get(f"/api/rooms/{room_id}/files", params={"email": viewer_email})
        assert r4.status_code == 200
        files = r4.json()["files"]
        assert any(f["id"] == file_id for f in files)

        # Viewer can preview via room-scoped preview
        r5 = client.get(f"/api/rooms/{room_id}/files/{file_id}/preview", params={"email": viewer_email})
        assert r5.status_code == 200
        assert r5.content == file_content

        # Viewer cannot delete
        r6 = client.delete(f"/api/rooms/{room_id}/files/{file_id}", params={"email": viewer_email})
        assert r6.status_code == 403

        # Owner can delete
        r7 = client.delete(f"/api/rooms/{room_id}/files/{file_id}", params={"email": owner_email})
        assert r7.status_code == 200
        assert r7.json()["deleted"] is True
        assert not os.path.exists(file_path)
