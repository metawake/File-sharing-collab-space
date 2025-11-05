export type DataroomFile = {
  id: number;
  name: string;
  mime_type?: string | null;
  size_bytes?: number | null;
  drive_file_id?: string | null;
  sha256?: string | null;
  created_at?: string | null;
};

export type Room = {
  id: number;
  name: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  created_at?: string | null;
};

export type RoomMember = {
  email: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  joined_at: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function requestJson(url: string, init?: RequestInit): Promise<any> {
  const res = await fetch(url, { credentials: 'include', ...init });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    let detail: string | undefined;
    try {
      const body = await res.json();
      detail = body?.detail || body?.message;
      if (detail) msg += ` - ${detail}`;
    } catch (_) {
      // ignore
    }
    throw new ApiError(res.status, msg, detail);
  }
  return res.json();
}

export function previewUrl(fileId: number, email: string) {
  const url = new URL(`${API_BASE}/api/files/${fileId}/preview`);
  if (email) url.searchParams.set('email', email);
  return url.toString();
}

export function previewRoomUrl(roomId: number, fileId: number, email: string) {
  const url = new URL(`${API_BASE}/api/rooms/${roomId}/files/${fileId}/preview`);
  if (email) url.searchParams.set('email', email);
  return url.toString();
}

export async function listFiles(email: string): Promise<DataroomFile[]> {
  const url = new URL(`${API_BASE}/api/files`);
  url.searchParams.set('email', email);
  const data = await requestJson(url.toString());
  return data.files as DataroomFile[];
}

export async function deleteFile(fileId: number, email: string): Promise<void> {
  const url = new URL(`${API_BASE}/api/files/${fileId}`);
  url.searchParams.set('email', email);
  await requestJson(url.toString(), { method: 'DELETE' });
}

export async function importFiles(email: string, driveFileIds: string[], roomId?: number): Promise<{ file_id: string; status: string }[]> {
  const data = await requestJson(`${API_BASE}/api/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, drive_file_ids: driveFileIds, room_id: roomId }),
  });
  return data.results as { file_id: string; status: string }[];
}

export async function logout(): Promise<void> {
  await requestJson(`${API_BASE}/auth/logout`, { method: 'POST' });
}

export async function getMe(): Promise<{ email: string | null }> {
  return await requestJson(`${API_BASE}/auth/me`);
}

export async function listRooms(email: string): Promise<Room[]> {
  const url = new URL(`${API_BASE}/api/rooms`);
  url.searchParams.set('email', email);
  const data = await requestJson(url.toString());
  return data.rooms as Room[];
}

export async function createRoom(email: string, name: string): Promise<Room> {
  const url = new URL(`${API_BASE}/api/rooms`);
  url.searchParams.set('email', email);
  return await requestJson(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

export async function listRoomFiles(roomId: number, email: string): Promise<DataroomFile[]> {
  const url = new URL(`${API_BASE}/api/rooms/${roomId}/files`);
  if (email) url.searchParams.set('email', email);
  const data = await requestJson(url.toString());
  return data.files as DataroomFile[];
}

export async function linkFileToRoom(roomId: number, fileId: number, email: string): Promise<void> {
  const url = new URL(`${API_BASE}/api/rooms/${roomId}/files`);
  url.searchParams.set('email', email);
  await requestJson(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId }),
  });
}

export async function deleteRoomFile(roomId: number, fileId: number, email: string): Promise<void> {
  const url = new URL(`${API_BASE}/api/rooms/${roomId}/files/${fileId}`);
  url.searchParams.set('email', email);
  await requestJson(url.toString(), { method: 'DELETE' });
}

export async function addRoomMember(roomId: number, memberEmail: string, role: string, email: string): Promise<void> {
  const url = new URL(`${API_BASE}/api/rooms/${roomId}/members`);
  url.searchParams.set('email', email);
  await requestJson(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: memberEmail, role }),
  });
}

export async function listRoomMembers(roomId: number, email: string): Promise<RoomMember[]> {
  const url = new URL(`${API_BASE}/api/rooms/${roomId}/members`);
  url.searchParams.set('email', email);
  const data = await requestJson(url.toString());
  return data.members as RoomMember[];
}

