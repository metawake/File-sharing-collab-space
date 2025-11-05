import { ReactNode } from 'react';

export function Modal({ open, onClose, children, title }: { open: boolean; onClose: () => void; children: ReactNode; title?: string }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative z-50 w-full max-w-3xl bg-white rounded shadow-lg border border-gray-200">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h3 className="font-semibold">{title || 'Modal'}</h3>
          <button className="text-gray-500 hover:text-gray-700" onClick={onClose}>✕</button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

