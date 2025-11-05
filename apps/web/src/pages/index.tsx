import Head from 'next/head';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { importFiles, ApiError, logout, listRooms, createRoom, getMe, addRoomMember, listRoomMembers } from '../utils/api';
import type { Room } from '../utils/api';
import { extractDriveIds } from '../utils/drive';
import { DriveBrowser } from '../components/DriveBrowser';
import { useToast } from '../components/ToastProvider';
import { DataRoomTable } from '../components/DataRoomTable';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

type RoomItem = {
  id: number;
  name: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  created_at?: string | null;
};

export default function Home() {
  const [email, setEmail] = useState('');
  const [ids, setIds] = useState('');
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const [reconnectNeeded, setReconnectNeeded] = useState(false);
  const [progress, setProgress] = useState<{ total: number; done: number } | null>(null);
  const qc = useQueryClient();
  const toast = useToast();
  const [browseOpen, setBrowseOpen] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [newRoomName, setNewRoomName] = useState('');
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('viewer');

  const connect = () => {
    window.location.href = `${API_BASE}/auth/google/login`;
  };

  const meQ = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
  });

  const sessionEmail = meQ.data?.email || '';

  useEffect(() => {
    try {
      if (email) localStorage.setItem('email', email);
    } catch (_) {}
  }, [email]);

  const doImport = useMutation({
    mutationFn: async (vars?: { idsOverride?: string[] }) => {
      setImportError(null);
      setImportSuccess(null);
      setReconnectNeeded(false);
      const driveFileIds = vars?.idsOverride ?? extractDriveIds(ids);
      const results: { file_id: string; status: string }[] = [];
      setProgress({ total: driveFileIds.length, done: 0 });
      for (const fid of driveFileIds) {
        try {
          const r = await importFiles(sessionEmail, [fid], selectedRoom?.id);
          results.push(r[0]);
        } catch (e) {
          // Represent as an error result for this file
          results.push({ file_id: fid, status: 'error' });
          throw e;
        } finally {
          setProgress((p) => (p ? { ...p, done: p.done + 1 } : p));
        }
      }
      return results;
    },
    onSuccess: (results) => {
      const imported = results.filter((r) => r.status === 'imported').length;
      const duplicates = results.filter((r) => r.status === 'duplicate').length;
      setImportSuccess(`Imported ${imported}, skipped ${duplicates} duplicate(s).`);
      if (imported) toast.add(`Imported ${imported} file(s)`, 'success');
      if (duplicates) toast.add(`Skipped ${duplicates} duplicate(s)`, 'info');
      qc.invalidateQueries({ queryKey: ['files', sessionEmail] });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        if (err.status === 401) setReconnectNeeded(true);
        setImportError(err.detail || err.message || 'Import failed');
      } else {
        setImportError('Import failed');
      }
    },
    onSettled: () => {
      setProgress(null);
    },
  });

  const roomsQ = useQuery<Room[]>({
    queryKey: ['rooms', sessionEmail || 'public'],
    queryFn: () => listRooms(sessionEmail),
    // Always attempt; backend will return public room when not authed
    enabled: true,
  });

  const createRoomMut = useMutation({
    mutationFn: () => createRoom(sessionEmail, newRoomName || 'New Room'),
    onSuccess: (room) => {
      qc.invalidateQueries({ queryKey: ['rooms', sessionEmail] });
      setSelectedRoom(room);
      setNewRoomName('');
      toast.add(`Created room "${room.name}"`, 'success');
    },
  });

  const addMemberMut = useMutation({
    mutationFn: () => {
      if (!selectedRoom) throw new Error('No room selected');
      return addRoomMember(selectedRoom.id, newMemberEmail, newMemberRole, sessionEmail);
    },
    onSuccess: () => {
      setNewMemberEmail('');
      setNewMemberRole('viewer');
      qc.invalidateQueries({ queryKey: ['members', selectedRoom?.id] });
      toast.add('Member added successfully', 'success');
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        toast.add(err.detail || 'Failed to add member', 'error');
      } else {
        toast.add('Failed to add member', 'error');
      }
    },
  });

  const membersQ = useQuery({
    queryKey: ['members', selectedRoom?.id],
    queryFn: () => selectedRoom ? listRoomMembers(selectedRoom.id, sessionEmail) : Promise.resolve([]),
    enabled: !!selectedRoom && !!sessionEmail,
  });

  const isAuthed = !!sessionEmail;
  const isRoomSelected = !!selectedRoom;
  const canImportToCurrent = !!sessionEmail && !!isRoomSelected && (selectedRoom ? ['owner', 'admin', 'editor'].includes(selectedRoom.role) : false);
  const filesTitle = isRoomSelected ? `Files in ${selectedRoom?.name}` : 'Files';
  const rooms: Array<RoomItem> = Array.isArray(roomsQ.data) ? roomsQ.data as RoomItem[] : [];

  const renderRoomButton = (room: RoomItem) => {
    const isSelected = selectedRoom?.id === room.id;
    return (
      <button
        key={room.id}
        className={`px-3 py-2 text-left rounded border ${isSelected ? 'bg-gray-100' : ''}`}
        onClick={() => setSelectedRoom(room as Room)}
        title={`Role: ${room.role}`}
      >
        <div className="flex items-center justify-between">
          <span>{room.name}</span>
          <span className="text-xs text-gray-500">{room.role}</span>
        </div>
      </button>
    );
  };

  // Auto-select the public demo room for logged-out users so the UI shows content immediately
  useEffect(() => {
    if (!isAuthed && !isRoomSelected && Array.isArray(roomsQ.data) && roomsQ.data.length === 1) {
      setSelectedRoom(roomsQ.data[0]);
    }
  }, [isAuthed, isRoomSelected, roomsQ.data]);

  return (
    <>
      <Head>
        <title>HarveyAI DataRoom</title>
      </Head>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white/90 border-b">
          <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-lg font-bold flex items-center gap-2">
                <span className="text-2xl">🔒</span>
                <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">HarvyAI DataRoom</span>
              </div>
              <span className="text-xs text-gray-500 hidden sm:inline">Secure Document Sharing</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              {isAuthed ? (
                <>
                  <span className="text-gray-700">Signed in as <span className="font-medium">{sessionEmail}</span></span>
                  <button
                    className="px-3 py-1.5 rounded border hover:bg-gray-50"
                    onClick={async () => {
                      try { await logout(); } catch (_) {}
                      try { localStorage.removeItem('email'); } catch (_) {}
                      setEmail('');
                      setIds('');
                      setBrowseOpen(false);
                      setSelectedRoom(null); // Reset to room list view
                      setNewRoomName(''); // Clear form
                      setNewMemberEmail(''); // Clear form
                      // Refetch data to show public room for logged-out users
                      qc.invalidateQueries({ queryKey: ['me'] });
                      qc.invalidateQueries({ queryKey: ['rooms'] });
                      toast.add('✅ Successfully logged out', 'success');
                    }}
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  <span className="text-gray-700">Not signed in</span>
                  <button className="px-3 py-1.5 rounded bg-blue-600 text-white" onClick={connect}>Sign in with Google</button>
                </>
              )}
            </div>
          </div>
        </header>
        <main className="max-w-5xl mx-auto p-4 space-y-4">
          {/* Welcome Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h1 className="text-2xl font-semibold mb-2">Welcome</h1>
            <p className="text-gray-600">
              {isAuthed 
                ? "Manage your secure data rooms and share files with authorized members." 
                : "Sign in with Google to create private rooms and import files from Drive. Or browse the public Demo Room below."}
            </p>
          </div>

        {reconnectNeeded && (
          <div className="bg-amber-50 border border-amber-300 text-amber-900 px-3 py-2 rounded">
            Token expired or revoked. Please reconnect Google Drive.
            <button className="ml-2 underline" onClick={connect}>Reconnect</button>
          </div>
        )}

        {/* Rooms Section */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-medium mb-3 flex items-center gap-2">
            <span>📁</span>
            <span>Rooms</span>
          </h2>
          {roomsQ.isLoading ? (
            <div>Loading rooms…</div>
          ) : roomsQ.isError ? (
            <div className="text-red-600">Failed to load rooms</div>
          ) : !isRoomSelected ? (
            <div>
              {isAuthed && (
                <div className="mb-4">
                  <label className="block text-sm text-gray-700 mb-1">New room</label>
                  <div className="flex items-center gap-2">
                    <input
                      value={newRoomName}
                      onChange={(e) => setNewRoomName(e.target.value)}
                      placeholder="Room name"
                      className="px-3 py-2 rounded border w-full"
                    />
                    <button className="px-3 py-2 rounded border whitespace-nowrap flex items-center gap-1" disabled={!newRoomName || createRoomMut.isPending} onClick={() => createRoomMut.mutate()}>
                      <span>➕</span>
                      <span>{createRoomMut.isPending ? 'Creating…' : 'Create'}</span>
                    </button>
                  </div>
                </div>
              )}
              <div className="text-sm">
                <div className="font-medium mb-2 text-gray-700">{isAuthed ? 'Your rooms' : 'Available rooms'}</div>
                <div className="flex flex-col gap-2">
                  {rooms.length === 0 && (
                    <div className="text-gray-500 text-sm">No rooms yet. Create one above.</div>
                  )}
                  {rooms.map(renderRoomButton)}
                </div>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm text-gray-700">
                  Viewing: <span className="font-medium">Room “{selectedRoom?.name}”</span> · Role: <span className="font-mono">{selectedRoom?.role}</span>
                </div>
                <button className="px-2 py-1 rounded border text-sm" onClick={() => setSelectedRoom(null)}>← Back to rooms</button>
              </div>

              {isAuthed && (
                <section className="bg-gray-50 rounded-lg p-5 -mx-6 mt-6 px-6">
                  <h2 className="text-xl font-medium mb-2 flex items-center gap-2">
                    <span>📥</span>
                    <span>Add Files from Google Drive</span>
                  </h2>
                  {canImportToCurrent ? (
                    <>
                      <p className="text-sm text-gray-600 mb-3">
                        Import documents from your Google Drive into <span className="font-medium">{selectedRoom?.name}</span>. 
                        Files will be securely stored and accessible only to authorized members.
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <input
                          value={ids}
                          onChange={(e) => setIds(e.target.value)}
                          placeholder="Paste Google Drive file URLs (comma-separated)"
                          className="px-3 py-2 rounded border min-w-[360px] flex-1"
                        />
                        <button className="px-3 py-2 rounded border hover:bg-white" onClick={() => setBrowseOpen(true)} disabled={!sessionEmail}>
                          📁 Browse Drive
                        </button>
                        <button className="px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50" onClick={() => doImport.mutate({})} disabled={!canImportToCurrent || doImport.isPending}>
                          {doImport.isPending ? 'Importing…' : 'Import Files'}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        ✓ Files remain in your Drive · ✓ Encrypted storage · ✓ Full audit trail
                      </div>
                      {progress && (
                        <div className="mt-2 w-full max-w-xl">
                          <div className="flex justify-between text-xs text-gray-600 mb-1">
                            <span>Importing files…</span>
                            <span>
                              {progress.done}/{progress.total}
                            </span>
                          </div>
                          <div className="h-2 bg-gray-200 rounded">
                            <div
                              className="h-2 bg-blue-600 rounded"
                              style={{ width: `${progress.total ? Math.min(100, Math.round((progress.done / progress.total) * 100)) : 0}%` }}
                            />
                          </div>
                        </div>
                      )}
                      {importError && <div className="text-red-600 mt-2">{importError}</div>}
                      {importSuccess && <div className="text-green-700 mt-2">{importSuccess}</div>}
                    </>
                  ) : (
                    <div className="text-sm text-gray-600">
                      You have <b>{selectedRoom?.role}</b> access in “{selectedRoom?.name}”. Only owner/admin/editor can import.
                    </div>
                  )}
                </section>
              )}

              {isAuthed && selectedRoom && ['owner', 'admin'].includes(selectedRoom.role) && (
                <section className="bg-blue-50 rounded-lg p-5 -mx-6 mt-6 px-6">
                  <h2 className="text-xl font-medium mb-4 flex items-center gap-2">
                    <span>👥</span>
                    <span>Members</span>
                    {membersQ.data && <span className="text-sm font-normal text-gray-600">({membersQ.data.length})</span>}
                  </h2>
                  
                  {/* Current Members List */}
                  {membersQ.isLoading ? (
                    <div className="text-sm text-gray-600 mb-4">Loading members…</div>
                  ) : membersQ.data && membersQ.data.length > 0 ? (
                    <div className="mb-5 bg-white rounded-lg overflow-hidden border">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b">
                          <tr>
                            <th className="text-left p-3 font-medium text-gray-700">Email</th>
                            <th className="text-left p-3 font-medium text-gray-700">Role</th>
                            <th className="text-left p-3 font-medium text-gray-700">Joined</th>
                          </tr>
                        </thead>
                        <tbody>
                          {membersQ.data.map((member) => (
                            <tr key={member.email} className="border-b last:border-b-0">
                              <td className="p-3">{member.email}</td>
                              <td className="p-3">
                                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                                  member.role === 'owner' ? 'bg-purple-100 text-purple-800' :
                                  member.role === 'admin' ? 'bg-blue-100 text-blue-800' :
                                  member.role === 'editor' ? 'bg-green-100 text-green-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {member.role}
                                </span>
                              </td>
                              <td className="p-3 text-gray-600">
                                {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}

                  {/* Add Member Form */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Add member</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="email"
                        value={newMemberEmail}
                        onChange={(e) => setNewMemberEmail(e.target.value)}
                        placeholder="Email address"
                        className="px-3 py-2 rounded border flex-1"
                      />
                      <select
                        value={newMemberRole}
                        onChange={(e) => setNewMemberRole(e.target.value)}
                        className="px-3 py-2 rounded border"
                        title="Viewer: Download only | Editor: Upload & download | Admin: Full control"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                      </select>
                      <button
                        className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-50 whitespace-nowrap"
                        disabled={!newMemberEmail || addMemberMut.isPending}
                        onClick={() => addMemberMut.mutate()}
                      >
                        {addMemberMut.isPending ? 'Adding…' : 'Invite'}
                      </button>
                    </div>
                    <div className="text-xs text-gray-600 mt-1.5">
                      💡 <b>Viewer:</b> Download only · <b>Editor:</b> Upload & download · <b>Admin:</b> Manage members & files
                    </div>
                  </div>
                </section>
              )}

              <section className="bg-white border border-gray-200 rounded-lg p-5 -mx-6 mt-6 px-6">
                <h2 className="text-xl font-medium mb-3 flex items-center gap-2">
                  <span>📄</span>
                  <span>{filesTitle}</span>
                </h2>
                {!isAuthed && (
                  <div className="bg-blue-50 border border-blue-200 rounded px-4 py-3 mb-4 text-sm text-blue-900">
                    👁️ You're viewing the Demo Room as a guest. <button onClick={connect} className="underline font-medium">Sign in</button> to create your own rooms and import files.
                  </div>
                )}
                <DataRoomTable email={sessionEmail} roomId={selectedRoom?.id} roleInRoom={selectedRoom?.role} />
              </section>
            </div>
          )}
        </section>

        <DriveBrowser
          open={browseOpen}
          onClose={() => setBrowseOpen(false)}
          email={sessionEmail}
          onImport={(selectedIds) => {
            // Trigger import immediately for selected items
            doImport.mutate({ idsOverride: selectedIds });
            // Also reflect in the input for visibility/history
            setIds((p) => (p ? p + ',' + selectedIds.join(',') : selectedIds.join(',')));
          }}
        />
        </main>
        </div>
    </>
  );
}

