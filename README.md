# DataRoom + Google Drive (FastAPI + Next.js)

Monorepo with `apps/api` (FastAPI) and `apps/web` (Next.js + TypeScript).

## Phase A (skeleton)
- FastAPI with `/healthz`, Google OAuth endpoints stubs
- SQLModel models and SQLite
- Next.js with React Query and "Connect Google Drive" button

## Local setup

### API
```bash
make api-install
make api-dev
```

### Web
```bash
make web-install
make web-dev
```

Set env:
- API: `apps/api/.env` (see `apps/api/.env.example`)
- Web: `apps/web/.env.local` (see `apps/web/.env.example`)

## Tests
```bash
make api-test
```

## Notes
- Core MVP includes Google OAuth, Drive import, file list/preview/delete with token refresh.

### Rooms & RBAC (demo)
- Backend models: `Room`, `Membership (owner/admin/editor/viewer)`, `FileRoomLink`, `AuditLog`.
- Endpoints:
  - `GET /api/rooms` — list rooms for current user (with role)
  - `POST /api/rooms { name }` — create a room (creator is owner)
  - `POST /api/rooms/{room_id}/members { email, role }` — add/update member (owner/admin)
  - `GET /api/rooms/{room_id}/files` — list files linked to the room
  - `POST /api/rooms/{room_id}/files { file_id }` — link a file to the room (editor+)
  - `GET /api/rooms/{room_id}/files/{file_id}/preview` — preview with room RBAC
  - `DELETE /api/rooms/{room_id}/files/{file_id}` — delete (owner/editor who uploaded)
- Import can optionally attach to a room: `POST /api/import { email, drive_file_ids, room_id? }`.
- Frontend: Rooms section to create/select a room; imports go to selected room; files table switches between "All my files" and selected room; actions gated by role.

Security & caveats
- Email query parameter is still accepted for tests and local demo; session cookie is preferred where available.
- Files are stored on local disk; no external blob storage. Do not expose local paths.
- Minimal audit log stored (actor, action, object, room); extend as needed.

## Deploy (Render + Vercel)

### 1) Render (API + Postgres)
- Create a new Blueprint on Render from `render.yaml` (root).
- In the service env, set:
  - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (from Google Cloud Console)
  - `WEB_BASE_URL=https://<your-vercel-domain>`
  - `API_BASE_URL=https://<your-render-service>` (optional)
  - `GOOGLE_REDIRECT_URI=https://<your-render-service>/auth/google/callback`
- Render will provision a Free Postgres DB and inject `DATABASE_URL` automatically.

### 2) Vercel (Web)
- Import the project, set root to `apps/web`.
- Set env var: `NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>`
- Build and deploy; Vercel auto-detects Next.js.

### 3) Google Cloud Console
- OAuth consent screen: External (Testing). Add reviewers as Test users.
- Credentials → OAuth 2.0 Client ID (Web app):
  - Authorized redirect URIs:
    - `http://localhost:8000/auth/google/callback` (local)
    - `https://<your-render-service>/auth/google/callback` (prod)
  - Authorized JavaScript origins (optional):
    - `http://localhost:3000`
    - `https://<your-vercel-domain>`

### 4) Security & CORS
- API restricts CORS to `WEB_BASE_URL` (and local origins if WEB_BASE_URL contains `localhost`).
- Security headers added: `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Strict-Transport-Security`.

### 5) Docker (local, optional)
```bash
docker compose up --build
# API http://localhost:8000, Web http://localhost:3000
```

### 6) Session
- After connecting Google, the API sets a signed session cookie and uses it server-side.
- Sign out via the UI button (calls `POST /auth/logout`).

