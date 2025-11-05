from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode, quote
import asyncio

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .db import init_db, engine
from .models import User, OAuthToken
from .models import Room, Membership, FileRoomLink, AuditLog
from sqlmodel import Session, select
import os
import hashlib
import pathlib

app = FastAPI(title=settings.app_name)

# CORS for web app (handles OPTIONS preflight)
origins = [settings.web_base_url.rstrip("/")]
if "localhost" in settings.web_base_url:
    origins += ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=True,
)


def get_session_email(request: Request, fallback_email: Optional[str]) -> Optional[str]:
    """
    Extract user email from session, with optional fallback for dev/testing.
    Only uses fallback when ALLOW_EMAIL_PARAM is enabled.
    """
    sess_email = None
    try:
        sess = request.session  # type: ignore[attr-defined]
        sess_email = sess.get("email") if isinstance(sess, dict) else None
    except Exception:
        sess_email = None
    if sess_email:
        return sess_email
    # Only allow fallback via query param when explicitly enabled (dev/tests)
    if settings.allow_email_param:
        return fallback_email
    return None


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )
    # Only meaningful over HTTPS; harmless otherwise
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
    )
    return response


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if settings.demo_seed:
        _seed_demo()


def _seed_demo() -> None:
    """Create a demo room with a couple of local files and set it public.
    Safe to call repeatedly; it won't duplicate content.
    """
    from .models import File as FileModel

    owner_email = "demo-owner@dataroom.local"
    room_name = settings.seed_room_name or "Demo Room"
    storage_dir = settings.storage_dir
    pathlib.Path(storage_dir).mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == owner_email)).first()
        if not user:
            user = User(email=owner_email)
            session.add(user)
            session.commit()
            session.refresh(user)

        room = session.exec(select(Room).where(Room.name == room_name)).first()
        if not room:
            room = Room(name=room_name)
            session.add(room)
            session.commit()
            session.refresh(room)
            session.add(Membership(user_id=user.id, room_id=room.id, role=Membership.Role.owner))  # type: ignore[arg-type]
            session.commit()

        # seed small text files if not present
        samples = [
            ("Welcome.txt", b"Welcome to the Demo Room. This is a sample document.\n"),
            ("Checklist.txt", b"- NDA signed\n- Data collection\n- Review complete\n"),
        ]
        for name, content in samples:
            dest = os.path.join(storage_dir, name)
            if not os.path.exists(dest):
                with open(dest, "wb") as f:
                    f.write(content)
            existing = session.exec(
                select(FileModel).where(
                    FileModel.user_id == user.id, FileModel.name == name
                )
            ).first()
            if not existing:
                frow = FileModel(
                    user_id=user.id,  # type: ignore[arg-type]
                    drive_file_id=None,
                    name=name,
                    mime_type="text/plain",
                    size_bytes=len(content),
                    local_path=dest,
                    sha256=hashlib.sha256(content).hexdigest(),
                )
                session.add(frow)
                session.commit()
                session.refresh(frow)
                link = session.exec(
                    select(FileRoomLink).where(
                        FileRoomLink.room_id == room.id, FileRoomLink.file_id == frow.id
                    )
                ).first()
                if not link:
                    session.add(FileRoomLink(room_id=room.id, file_id=frow.id))
                    session.commit()

        # Mark this room as public for unauthenticated viewing
        try:
            settings.public_room_id = settings.public_room_id or room.id
        except Exception:
            pass


@app.get("/healthz")
def healthz() -> JSONResponse:
    """Health check endpoint for monitoring and load balancers."""
    return JSONResponse({"status": "ok"})


@app.get("/auth/me")
def auth_me(request: Request) -> JSONResponse:
    """Return the current user's email from session, or null if not authenticated."""
    email = get_session_email(request, None)
    return JSONResponse({"email": email})


@app.get("/auth/google/login")
def google_login() -> RedirectResponse:
    """Initiate Google OAuth flow for Drive access and user authentication."""
    if not (settings.google_client_id and settings.google_redirect_uri):
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "hl": "en",  # Force English language
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(auth_url, status_code=302)


@app.get("/auth/google/callback")
async def google_callback(
    request: Request, code: Optional[str] = None, error: Optional[str] = None
) -> JSONResponse:
    """
    Handle Google OAuth callback, exchange code for tokens, and create user session.
    Stores refresh token for offline Drive access.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if not (
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_redirect_uri
    ):
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    # Exchange code for tokens
    token_endpoint = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.post(token_endpoint, data=data)
    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=400, detail=f"Token exchange failed: {token_resp.text}"
        )

    tokens = token_resp.json()

    # Fetch user info to get email
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=400, detail="Missing access_token in token response"
        )

    async with httpx.AsyncClient(timeout=20.0) as client:
        userinfo_resp = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if userinfo_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")
    userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="User info missing email")

    # Persist user and tokens
    expires_in = tokens.get("expires_in")
    expires_at: Optional[datetime] = None
    if isinstance(expires_in, int):
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    with Session(engine) as session:
        # Upsert user
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user is None:
            existing_user = User(email=email)
            session.add(existing_user)
            session.commit()
            session.refresh(existing_user)

        # Upsert token
        token_row = session.exec(
            select(OAuthToken).where(
                OAuthToken.user_id == existing_user.id,  # type: ignore[arg-type]
                OAuthToken.provider == "google",
            )
        ).first()

        now = datetime.utcnow()
        if token_row is None:
            token_row = OAuthToken(
                user_id=existing_user.id,  # type: ignore[arg-type]
                provider="google",
                access_token=access_token,
                refresh_token=tokens.get("refresh_token"),
                expires_at=expires_at,
                scope=tokens.get("scope"),
                token_type=tokens.get("token_type"),
                created_at=now,
                updated_at=now,
            )
            session.add(token_row)
        else:
            token_row.access_token = access_token
            token_row.refresh_token = (
                tokens.get("refresh_token") or token_row.refresh_token
            )
            token_row.expires_at = expires_at
            token_row.scope = tokens.get("scope")
            token_row.token_type = tokens.get("token_type")
            token_row.updated_at = now

        session.commit()

    # Persist session for server-side identity
    try:
        request.session["email"] = email  # type: ignore[index]
    except Exception:
        pass
    redirect = settings.web_base_url.rstrip("/") + f"/?connected=1&email={quote(email)}"
    return RedirectResponse(redirect, status_code=302)


@app.post("/auth/logout")
def logout(request: Request) -> JSONResponse:
    """Clear user session and log out."""
    try:
        # clear server-side session
        request.session.clear()  # type: ignore[assignment]
    except Exception:
        pass
    return JSONResponse({"ok": True})


from pydantic import BaseModel
from .google import GoogleDriveClient, TokenBundle


class ImportRequest(BaseModel):
    email: str
    drive_file_ids: List[str]
    room_id: Optional[int] = None


def _safe_filename(name: str) -> str:
    """Sanitize filename by replacing path separators with underscores."""
    candidate = name.replace("/", "_").replace("\\", "_")
    return candidate or "file"


async def _import_one(
    user: User,
    file_id: str,
    storage_dir: str,
    tokens: OAuthToken,
) -> Dict[str, Any]:
    """
    Import a single file from Google Drive.
    Returns a dict with status: 'imported', 'duplicate', or 'error'.
    """
    client = GoogleDriveClient(TokenBundle(tokens.access_token, tokens.refresh_token))
    try:
        status, meta = await client.get_metadata_with_refresh(
            file_id,
            settings.google_client_id or "",
            settings.google_client_secret or "",
        )
        if status != 200:
            return {"file_id": file_id, "status": "error", "error": "metadata_failed"}
        name = _safe_filename(meta.get("name") or file_id)
        mime_type = meta.get("mimeType")
        size_str = meta.get("size")
        size_bytes = int(size_str) if size_str and size_str.isdigit() else None

        # check duplicates by drive_file_id
        from .models import File as FileModel

        with Session(engine) as session:
            existing = session.exec(
                select(FileModel).where(
                    FileModel.user_id == user.id, FileModel.drive_file_id == file_id
                )
            ).first()
            if existing:
                return {
                    "file_id": file_id,
                    "status": "duplicate",
                    "by": "drive_file_id",
                    "id": existing.id,
                }

        # First try normal client (plays nice with our tests/mocks). If it fails, try streaming path.
        sha256_hex = None
        pathlib.Path(storage_dir).mkdir(parents=True, exist_ok=True)
        dest = os.path.join(storage_dir, name)
        base, ext = os.path.splitext(dest)
        idx = 1
        while os.path.exists(dest):
            dest = f"{base} ({idx}){ext}"
            idx += 1

        status, content_bytes, headers = await client.download_with_refresh(
            file_id,
            settings.google_client_id or "",
            settings.google_client_secret or "",
        )
        if status == 200 and content_bytes:
            with open(dest, "wb") as f:
                f.write(content_bytes)
            sha256_hex = hashlib.sha256(content_bytes).hexdigest()
        else:
            # Stream download for robustness (lower memory) and compute sha256 incrementally
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            for attempt in range(2):
                async with httpx.AsyncClient(timeout=60.0) as raw_client:
                    async with raw_client.stream(
                        "GET",
                        url,
                        headers={
                            "Authorization": f"Bearer {client.tokens.access_token}"
                        },
                    ) as resp:
                        if (
                            resp.status_code == 401
                            and await client._refresh_access_token(
                                settings.google_client_id or "",
                                settings.google_client_secret or "",
                            )
                            and attempt == 0
                        ):
                            continue
                        if resp.status_code != 200:
                            return {
                                "file_id": file_id,
                                "status": "error",
                                "error": "download_failed",
                            }
                        hasher = hashlib.sha256()
                        with open(dest, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                if not chunk:
                                    continue
                                f.write(chunk)
                                hasher.update(chunk)
                        sha256_hex = hasher.hexdigest()
                        break

        with Session(engine) as session:
            dup_hash = session.exec(
                select(FileModel).where(
                    FileModel.user_id == user.id, FileModel.sha256 == sha256_hex
                )
            ).first()
            if dup_hash:
                return {
                    "file_id": file_id,
                    "status": "duplicate",
                    "by": "sha256",
                    "id": dup_hash.id,
                }

        # write to storage
        # persist DB
        with Session(engine) as session:
            from .models import File as FileModel

            file_row = FileModel(
                user_id=user.id,  # type: ignore[arg-type]
                drive_file_id=file_id,
                name=os.path.basename(dest),
                mime_type=mime_type,
                size_bytes=size_bytes,
                local_path=dest,
                sha256=sha256_hex,
            )
            session.add(file_row)
            session.commit()
            session.refresh(file_row)
            # tokens may have been refreshed; ensure persisted if updated
            if client.tokens.access_token != tokens.access_token:
                tokens.access_token = client.tokens.access_token
                session.add(tokens)
                session.commit()
            return {"file_id": file_id, "status": "imported", "id": file_row.id}
    finally:
        await client.aclose()


@app.post("/api/import")
async def import_files(req: ImportRequest, request: Request) -> JSONResponse:
    """
    Import files from Google Drive into the data room.
    Optionally link imported files to a specific room.
    """
    if not req.drive_file_ids:
        raise HTTPException(status_code=400, detail="drive_file_ids is required")
    if not (settings.google_client_id and settings.google_client_secret):
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
    active_email = get_session_email(request, req.email)
    if not active_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == active_email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        token = session.exec(
            select(OAuthToken).where(
                OAuthToken.user_id == user.id, OAuthToken.provider == "google"
            )
        ).first()
        if not token:
            raise HTTPException(status_code=401, detail="Not connected to Google")

    # Import all files concurrently
    import_tasks = [_import_one(user, fid, settings.storage_dir, token) for fid in req.drive_file_ids]
    results = await asyncio.gather(*import_tasks)
    
    # Link imported files to room if specified
    if req.room_id:
        with Session(engine) as session:
            # Ensure permission to add files to room
            _ensure_role(session, user.id, req.room_id, ["owner", "admin", "editor"])  # type: ignore[arg-type]
            for outcome in results:
                if outcome.get("status") == "imported" and outcome.get("id"):
                    existing = session.exec(
                        select(FileRoomLink).where(FileRoomLink.room_id == req.room_id, FileRoomLink.file_id == outcome["id"])  # type: ignore[index]
                    ).first()
                    if not existing:
                        link = FileRoomLink(room_id=req.room_id, file_id=outcome["id"])  # type: ignore[arg-type]
                        session.add(link)
                        _log_action(
                            session,
                            actor_user_id=user.id,
                            action="room.link_file",
                            object_type="file",
                            object_id=outcome["id"],
                            room_id=req.room_id,
                        )
            session.commit()
    
    return JSONResponse({"results": list(results)})


@app.get("/api/drive/files")
async def drive_files(
    request: Request,
    email: Optional[str] = None,
    q: Optional[str] = None,
    page_token: Optional[str] = None,
) -> JSONResponse:
    """Browse user's Google Drive files with search and pagination support."""
    active_email = get_session_email(request, email)
    if not active_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == active_email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        token = session.exec(
            select(OAuthToken).where(
                OAuthToken.user_id == user.id, OAuthToken.provider == "google"
            )
        ).first()
        if not token:
            raise HTTPException(status_code=401, detail="Not connected to Google")

    client = GoogleDriveClient(TokenBundle(token.access_token, token.refresh_token))
    try:
        status, data = await client.list_with_refresh(
            settings.google_client_id or "",
            settings.google_client_secret or "",
            q=q,
            page_token=page_token,
        )
        if status != 200:
            raise HTTPException(status_code=400, detail="Failed to list files")
        return JSONResponse(data)
    finally:
        await client.aclose()


@app.get("/api/files")
def list_files(request: Request, email: Optional[str] = None) -> JSONResponse:
    """List all files imported by the authenticated user."""
    active_email = get_session_email(request, email)
    if not active_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from .models import File as FileModel

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == active_email)).first()
        if not user:
            return JSONResponse({"files": []})
        user_files = session.exec(
            select(FileModel).where(FileModel.user_id == user.id)
        ).all()
        payload = [
            {
                "id": f.id,
                "name": f.name,
                "mime_type": f.mime_type,
                "size_bytes": f.size_bytes,
                "drive_file_id": f.drive_file_id,
                "sha256": f.sha256,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "uploaded_by": active_email,  # User's own files
            }
            for f in user_files
        ]
        return JSONResponse({"files": payload})


@app.get("/api/files/{file_id}/preview")
def preview_file(request: Request, file_id: int, email: Optional[str] = None):
    active_email = get_session_email(request, email)
    if not active_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from .models import File as FileModel

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == active_email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        file = session.get(FileModel, file_id)
        if not file or file.user_id != user.id:
            raise HTTPException(status_code=404, detail="File not found")
        if not file.local_path or not os.path.exists(file.local_path):
            raise HTTPException(status_code=404, detail="Local file missing")
        return FileResponse(
            path=file.local_path,
            media_type=file.mime_type or "application/octet-stream",
            filename=file.name,
        )


@app.delete("/api/files/{file_id}")
def delete_file(
    request: Request, file_id: int, email: Optional[str] = None
) -> JSONResponse:
    active_email = get_session_email(request, email)
    if not active_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    from .models import File as FileModel

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == active_email)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        file = session.get(FileModel, file_id)
        if not file or file.user_id != user.id:
            raise HTTPException(status_code=404, detail="File not found")
        if file.local_path and os.path.exists(file.local_path):
            try:
                os.remove(file.local_path)
            except OSError:
                pass
        session.delete(file)
        session.commit()
        return JSONResponse({"deleted": True})


# -----------------
# Rooms & RBAC APIs
# -----------------


def _log_action(
    session: Session,
    *,
    actor_user_id: Optional[int],
    action: str,
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    room_id: Optional[int] = None,
    request: Optional[Request] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record an action in the audit log for security and compliance tracking."""
    ip = None
    ua = None
    try:
        if request is not None:
            ip = request.client.host if request.client else None  # type: ignore[assignment]
            ua = request.headers.get("user-agent")
    except Exception:
        pass
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        room_id=room_id,
        ip=ip,
        user_agent=ua,
        metadata_json=None,
    )
    session.add(entry)


def _get_active_user(
    session: Session, request: Request, fallback_email: Optional[str]
) -> Optional[User]:
    """Retrieve the active user from session or fallback email parameter."""
    active_email = get_session_email(request, fallback_email)
    if not active_email:
        return None
    return session.exec(select(User).where(User.email == active_email)).first()


def _get_membership(
    session: Session, user_id: int, room_id: int
) -> Optional[Membership]:
    """Get a user's membership record for a specific room."""
    return session.exec(
        select(Membership).where(
            Membership.user_id == user_id, Membership.room_id == room_id
        )
    ).first()


def _ensure_role(
    session: Session, user_id: int, room_id: int, allowed: List[str]
) -> None:
    """Check if user has one of the allowed roles in the room. Raises 403 if not."""
    m = _get_membership(session, user_id, room_id)
    if not m or (getattr(m.role, "value", m.role) not in allowed):
        raise HTTPException(status_code=403, detail="Forbidden")


class CreateRoomRequest(BaseModel):
    name: str


@app.get("/api/rooms")
def list_rooms(request: Request, email: Optional[str] = None) -> JSONResponse:
    """List all data rooms the user has access to, with their role in each room."""
    with Session(engine) as session:
        user = _get_active_user(session, request, email)
        if not user:
            # If a public room is configured, expose it for unauthenticated users as viewer
            if settings.public_room_id:
                r = session.get(Room, settings.public_room_id)
                if r:
                    return JSONResponse(
                        {
                            "rooms": [
                                {
                                    "id": r.id,
                                    "name": r.name,
                                    "role": "viewer",
                                    "created_at": (
                                        r.created_at.isoformat()
                                        if getattr(r, "created_at", None)
                                        else None
                                    ),
                                }
                            ]
                        }
                    )
            raise HTTPException(status_code=401, detail="Not authenticated")
        rows = session.exec(
            select(Room, Membership).where(
                Membership.user_id == user.id, Membership.room_id == Room.id
            )
        ).all()
        payload = [
            {
                "id": r.Room.id,
                "name": r.Room.name,
                "role": getattr(r.Membership.role, "value", r.Membership.role),
                "created_at": r.Room.created_at.isoformat(),
            }
            for r in rows
        ]
        return JSONResponse({"rooms": payload})


@app.post("/api/rooms")
def create_room(
    req: CreateRoomRequest, request: Request, email: Optional[str] = None
) -> JSONResponse:
    """Create a new data room. The creator becomes the owner."""
    with Session(engine) as session:
        user = _get_active_user(session, request, email)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        room = Room(name=req.name)
        session.add(room)
        session.commit()
        session.refresh(room)
        membership = Membership(user_id=user.id, room_id=room.id, role="owner")  # type: ignore[arg-type]
        session.add(membership)
        _log_action(
            session,
            actor_user_id=user.id,
            action="room.create",
            object_type="room",
            object_id=room.id,
            room_id=room.id,
            request=request,
        )
        session.commit()
        return JSONResponse({"id": room.id, "name": room.name})


class AddMemberRequest(BaseModel):
    email: str
    role: str


@app.post("/api/rooms/{room_id}/members")
def add_member(
    room_id: int, req: AddMemberRequest, request: Request, email: Optional[str] = None
) -> JSONResponse:
    """Add a member to a data room. Requires owner or admin role."""
    if req.role not in ["admin", "editor", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    with Session(engine) as session:
        actor = _get_active_user(session, request, email)
        if not actor:
            raise HTTPException(status_code=401, detail="Not authenticated")
        # Only owner or admin may add members
        _ensure_role(session, actor.id, room_id, ["owner", "admin"])  # type: ignore[arg-type]

        # Upsert target user by email
        target = session.exec(select(User).where(User.email == req.email)).first()
        if not target:
            target = User(email=req.email)
            session.add(target)
            session.commit()
            session.refresh(target)

        existing = _get_membership(session, target.id, room_id)  # type: ignore[arg-type]
        if existing:
            # type: ignore[attr-defined]
            existing.role = Membership.Role(req.role)  # type: ignore[assignment]
        else:
            session.add(Membership(user_id=target.id, room_id=room_id, role=Membership.Role(req.role)))  # type: ignore[arg-type]

        _log_action(
            session,
            actor_user_id=actor.id,
            action="room.add_member",
            object_type="room",
            object_id=room_id,
            room_id=room_id,
            request=request,
        )
        session.commit()
        return JSONResponse({"ok": True})


@app.get("/api/rooms/{room_id}/members")
def list_room_members(
    room_id: int, request: Request, email: Optional[str] = None
) -> JSONResponse:
    """List all members of a data room with their roles. Requires room membership."""
    with Session(engine) as session:
        actor = _get_active_user(session, request, email)
        if not actor:
            raise HTTPException(status_code=401, detail="Not authenticated")
        # Any member can view the member list
        _ensure_role(session, actor.id, room_id, ["owner", "admin", "editor", "viewer"])  # type: ignore[arg-type]
        
        memberships = session.exec(
            select(Membership, User).where(
                Membership.room_id == room_id,
                Membership.user_id == User.id
            )
        ).all()
        
        payload = [
            {
                "email": m.User.email,
                "role": getattr(m.Membership.role, "value", m.Membership.role),
                "joined_at": m.Membership.created_at.isoformat() if m.Membership.created_at else None,
            }
            for m in memberships
        ]
        return JSONResponse({"members": payload})


@app.get("/api/rooms/{room_id}/files")
def room_files(
    room_id: int, request: Request, email: Optional[str] = None
) -> JSONResponse:
    """List all files in a specific data room. Requires room membership."""
    from .models import File as FileModel

    with Session(engine) as session:
        user = _get_active_user(session, request, email)
        if not user:
            # Allow unauthenticated read for the configured public room
            if settings.public_room_id and room_id == settings.public_room_id:
                links = session.exec(
                    select(FileRoomLink).where(FileRoomLink.room_id == room_id)
                ).all()
                file_ids = [ln.file_id for ln in links]
                # Get files and user info separately for reliability
                if file_ids:
                    files_list = session.exec(
                        select(FileModel).where(FileModel.id.in_(file_ids))
                    ).all()
                    # Get all uploader user_ids
                    user_ids = list(set(f.user_id for f in files_list))
                    users = session.exec(select(User).where(User.id.in_(user_ids))).all()
                    user_map = {u.id: u.email for u in users}
                else:
                    files_list = []
                    user_map = {}
                payload = [
                    {
                        "id": f.id,
                        "name": f.name,
                        "mime_type": f.mime_type,
                        "size_bytes": f.size_bytes,
                        "drive_file_id": f.drive_file_id,
                        "sha256": f.sha256,
                        "created_at": (
                            f.created_at.isoformat() if f.created_at else None
                        ),
                        "uploaded_by": user_map.get(f.user_id, "Unknown"),
                    }
                    for f in files_list
                ]
                return JSONResponse({"files": payload})
            raise HTTPException(status_code=401, detail="Not authenticated")
        # Any member may view
        _ensure_role(session, user.id, room_id, ["owner", "admin", "editor", "viewer"])  # type: ignore[arg-type]
        links = session.exec(
            select(FileRoomLink).where(FileRoomLink.room_id == room_id)
        ).all()
        file_ids = [ln.file_id for ln in links]
        if not file_ids:
            return JSONResponse({"files": []})
        # Get files and user info separately for reliability
        files_list = session.exec(select(FileModel).where(FileModel.id.in_(file_ids))).all()
        # Get all uploader user_ids
        user_ids = list(set(f.user_id for f in files_list))
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        user_map = {u.id: u.email for u in users}
        
        payload = [
            {
                "id": f.id,
                "name": f.name,
                "mime_type": f.mime_type,
                "size_bytes": f.size_bytes,
                "drive_file_id": f.drive_file_id,
                "sha256": f.sha256,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "uploaded_by": user_map.get(f.user_id, "Unknown"),
            }
            for f in files_list
        ]
        return JSONResponse({"files": payload})


class LinkFileRequest(BaseModel):
    file_id: int


@app.post("/api/rooms/{room_id}/files")
def link_file(
    room_id: int, req: LinkFileRequest, request: Request, email: Optional[str] = None
) -> JSONResponse:
    from .models import File as FileModel

    with Session(engine) as session:
        user = _get_active_user(session, request, email)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        # editor+ may link files to a room
        _ensure_role(session, user.id, room_id, ["owner", "admin", "editor"])  # type: ignore[arg-type]
        f = session.get(FileModel, req.file_id)
        if not f or f.user_id != user.id:
            raise HTTPException(status_code=404, detail="File not found")
        existing = session.exec(
            select(FileRoomLink).where(
                FileRoomLink.room_id == room_id, FileRoomLink.file_id == req.file_id
            )
        ).first()
        if existing:
            return JSONResponse({"linked": True, "id": existing.id})
        link = FileRoomLink(room_id=room_id, file_id=req.file_id)
        session.add(link)
        _log_action(
            session,
            actor_user_id=user.id,
            action="room.link_file",
            object_type="file",
            object_id=req.file_id,
            room_id=room_id,
            request=request,
        )
        session.commit()
        session.refresh(link)
        return JSONResponse({"linked": True, "id": link.id})


@app.get("/api/rooms/{room_id}/files/{file_id}/preview")
def preview_room_file(
    room_id: int, file_id: int, request: Request, email: Optional[str] = None
):
    from .models import File as FileModel

    with Session(engine) as session:
        user = _get_active_user(session, request, email)
        if not user:
            if settings.public_room_id and room_id == settings.public_room_id:
                link = session.exec(
                    select(FileRoomLink).where(
                        FileRoomLink.room_id == room_id, FileRoomLink.file_id == file_id
                    )
                ).first()
                if not link:
                    raise HTTPException(status_code=404, detail="File not in room")
                f = session.get(FileModel, file_id)
                if not f or not f.local_path or not os.path.exists(f.local_path):
                    raise HTTPException(status_code=404, detail="File not found")
                return FileResponse(
                    path=f.local_path,
                    media_type=f.mime_type or "application/octet-stream",
                    filename=f.name,
                )
            raise HTTPException(status_code=401, detail="Not authenticated")
        # Any member may view
        _ensure_role(session, user.id, room_id, ["owner", "admin", "editor", "viewer"])  # type: ignore[arg-type]
        link = session.exec(
            select(FileRoomLink).where(
                FileRoomLink.room_id == room_id, FileRoomLink.file_id == file_id
            )
        ).first()
        if not link:
            raise HTTPException(status_code=404, detail="File not in room")
        f = session.get(FileModel, file_id)
        if not f or not f.local_path or not os.path.exists(f.local_path):
            raise HTTPException(status_code=404, detail="File not found")
        _log_action(
            session,
            actor_user_id=user.id,
            action="room.preview_file",
            object_type="file",
            object_id=file_id,
            room_id=room_id,
            request=request,
        )
        session.commit()
        return FileResponse(
            path=f.local_path,
            media_type=f.mime_type or "application/octet-stream",
            filename=f.name,
        )


@app.delete("/api/rooms/{room_id}/files/{file_id}")
def delete_room_file(
    room_id: int, file_id: int, request: Request, email: Optional[str] = None
) -> JSONResponse:
    from .models import File as FileModel

    with Session(engine) as session:
        user = _get_active_user(session, request, email)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        # editor+ may delete
        _ensure_role(session, user.id, room_id, ["owner", "admin", "editor"])  # type: ignore[arg-type]
        link = session.exec(
            select(FileRoomLink).where(
                FileRoomLink.room_id == room_id, FileRoomLink.file_id == file_id
            )
        ).first()
        if not link:
            raise HTTPException(status_code=404, detail="File not in room")
        f = session.get(FileModel, file_id)
        if not f:
            raise HTTPException(status_code=404, detail="File not found")
        # Only allow deleting if requester is the file owner (uploader)
        if f.user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if f.local_path and os.path.exists(f.local_path):
            try:
                os.remove(f.local_path)
            except OSError:
                pass
        session.delete(f)
        _log_action(
            session,
            actor_user_id=user.id,
            action="room.delete_file",
            object_type="file",
            object_id=file_id,
            room_id=room_id,
            request=request,
        )
        session.commit()
        return JSONResponse({"deleted": True})
