import { useEffect, useState } from 'react';
import { Modal } from './Modal';
import { formatBytes } from '../utils/format';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

type DriveFile = { id: string; name: string; mimeType?: string; size?: string };

export function DriveBrowser({ open, onClose, email, onImport }: { open: boolean; onClose: () => void; email: string; onImport: (ids: string[]) => void }) {
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageToken, setPageToken] = useState<string | null>(null);

  async function load(token?: string) {
    setLoading(true);
    setError(null);
    try {
      const url = new URL(`${API_BASE}/api/drive/files`);
      url.searchParams.set('email', email);
      if (token) url.searchParams.set('page_token', token);
      const res = await fetch(url.toString(), { credentials: 'include' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFiles((prev) => (token ? [...prev, ...data.files] : data.files));
      setPageToken(data.nextPageToken || null);
    } catch (e: any) {
      setError(e?.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open && email) {
      setFiles([]);
      setSelected({});
      setPageToken(null);
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, email]);

  const ids = Object.keys(selected).filter((k) => selected[k]);

  return (
    <Modal open={open} onClose={onClose} title="Browse Google Drive">
      {error && <div className="text-red-600 mb-2">{error}</div>}
      <div className="max-h-[60vh] overflow-auto border rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="text-left p-2 w-10"></th>
              <th className="text-left p-2">Name</th>
              <th className="text-left p-2">Type</th>
              <th className="text-right p-2">Size</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id} className="border-t">
                <td className="p-2">
                  <input type="checkbox" checked={!!selected[f.id]} onChange={(e) => setSelected((s) => ({ ...s, [f.id]: e.target.checked }))} />
                </td>
                <td className="p-2">{f.name}</td>
                <td className="p-2 text-gray-600">{f.mimeType || '—'}</td>
                <td className="p-2 text-right text-gray-600">{formatBytes(f.size)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <div className="p-2 text-sm text-gray-600">Loading…</div>}
        {!loading && pageToken && (
          <button className="m-2 px-3 py-1 text-sm rounded border" onClick={() => load(pageToken || undefined)}>Load more</button>
        )}
      </div>

      <div className="mt-3 flex justify-end gap-2">
        <button className="px-3 py-2 rounded border" onClick={onClose}>Cancel</button>
        <button className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-50" disabled={!ids.length} onClick={() => { onImport(ids); onClose(); }}>Import selected ({ids.length})</button>
      </div>
    </Modal>
  );
}

