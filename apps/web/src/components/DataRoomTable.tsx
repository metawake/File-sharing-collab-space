import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DataroomFile, listFiles, deleteFile, previewUrl, ApiError, listRoomFiles, previewRoomUrl, deleteRoomFile } from '../utils/api';
import { useMemo, useState } from 'react';
import { Modal } from './Modal';
import { formatBytes } from '../utils/format';

type Props = {
  email: string;
  roomId?: number;
  roleInRoom?: 'owner' | 'admin' | 'editor' | 'viewer';
};

export function DataRoomTable({ email, roomId, roleInRoom }: Props) {
  const [toDelete, setToDelete] = useState<DataroomFile | null>(null);
  const [sort, setSort] = useState<{ key: 'created_at' | 'name' | 'size_bytes'; dir: 'asc' | 'desc' }>({ key: 'created_at', dir: 'desc' });
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ['files', email, roomId || null],
    queryFn: () => (roomId ? listRoomFiles(roomId, email) : listFiles(email)),
    enabled: !!roomId || !!email, // Allow fetching for public rooms even without email
  });

  const del = useMutation({
    mutationFn: (fileId: number) => (roomId ? deleteRoomFile(roomId, fileId, email) : deleteFile(fileId, email)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['files', email, roomId || null] }),
  });

  const files = (q.data || []) as DataroomFile[];
  const sorted = useMemo(() => {
    const arr = [...files];
    const dir = sort.dir === 'asc' ? 1 : -1;
    arr.sort((a, b) => {
      let av: number | string = '';
      let bv: number | string = '';
      if (sort.key === 'name') {
        av = a.name.toLowerCase();
        bv = b.name.toLowerCase();
      } else if (sort.key === 'size_bytes') {
        av = a.size_bytes || 0;
        bv = b.size_bytes || 0;
      } else {
        av = a.created_at ? Date.parse(a.created_at) : 0;
        bv = b.created_at ? Date.parse(b.created_at) : 0;
      }
      if (av > bv) return 1 * dir;
      if (av < bv) return -1 * dir;
      return 0;
    });
    return arr;
  }, [files, sort]);

  function toggleSort(key: 'created_at' | 'name' | 'size_bytes') {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }));
  }

  let content: JSX.Element;
  if (!email && !roomId) {
    content = <div className="text-gray-500">Enter your email to view files.</div>;
  } else if (q.isLoading) {
    content = <div>Loading files…</div>;
  } else if (q.isError) {
    const err = q.error as Error;
    content = <div style={{ color: 'crimson' }}>Failed to load files{err.message ? `: ${err.message}` : ''}.</div>;
  } else if (sorted.length === 0) {
    content = <div className="text-gray-500">No files yet.</div>;
  } else {
    content = (
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2 cursor-pointer select-none" onClick={() => toggleSort('name')}>
              Name {sort.key === 'name' ? (sort.dir === 'asc' ? '▲' : '▼') : ''}
            </th>
            <th className="text-left p-2">Type</th>
            <th className="text-right p-2 cursor-pointer select-none" onClick={() => toggleSort('size_bytes')}>
              Size {sort.key === 'size_bytes' ? (sort.dir === 'asc' ? '▲' : '▼') : ''}
            </th>
            <th className="text-right p-2 cursor-pointer select-none" onClick={() => toggleSort('created_at')}>
              Created {sort.key === 'created_at' ? (sort.dir === 'asc' ? '▲' : '▼') : ''}
            </th>
            <th className="text-right p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((f) => (
            <tr key={f.id} className="border-b hover:bg-gray-50">
              <td className="p-2">{f.name}</td>
              <td className="p-2 text-gray-600">{f.mime_type || '—'}</td>
              <td className="p-2 text-right text-gray-600">{formatBytes(f.size_bytes)}</td>
              <td className="p-2 text-right text-gray-600">{f.created_at ? new Date(f.created_at).toLocaleString() : '—'}</td>
              <td className="p-2 text-right">
                <a className="text-blue-600 hover:underline mr-2 inline-flex items-center gap-1" href={roomId ? previewRoomUrl(roomId, f.id, email) : previewUrl(f.id, email)} target="_blank" rel="noreferrer" download>
                  <span>⬇️</span>
                  <span>Download</span>
                </a>
                {(!roomId || (roleInRoom && roleInRoom !== 'viewer')) && (
                  <button className="px-2 py-1 rounded border inline-flex items-center gap-1" onClick={() => setToDelete(f)} disabled={del.isPending}>
                    <span>🗑️</span>
                    <span>{del.isPending ? 'Deleting…' : 'Delete'}</span>
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <>
    {content}
    <Modal open={!!toDelete} onClose={() => setToDelete(null)} title="Delete file?">
      <p className="text-sm text-gray-700">
        This will remove <span className="font-medium">{toDelete?.name}</span> from your DataRoom (local copy only). It will NOT delete from Google Drive.
      </p>
      <div className="mt-4 flex justify-end gap-2">
        <button className="px-3 py-2 rounded border" onClick={() => setToDelete(null)} disabled={del.isPending}>Cancel</button>
        <button
          className="px-3 py-2 rounded bg-red-600 text-white disabled:opacity-50"
          onClick={() => {
            if (toDelete) del.mutate(toDelete.id, { onSuccess: () => setToDelete(null) });
          }}
          disabled={del.isPending}
        >
          Delete
        </button>
      </div>
    </Modal>
    </>
  );
}

