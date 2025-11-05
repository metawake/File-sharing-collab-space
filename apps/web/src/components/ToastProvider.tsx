import { createContext, useContext, useState, ReactNode, useCallback } from 'react';

type Toast = { id: number; message: string; variant?: 'success' | 'error' | 'info' };

const ToastCtx = createContext<{ add: (message: string, variant?: Toast['variant']) => void } | null>(null);

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const add = useCallback((message: string, variant?: Toast['variant']) => {
    const id = Date.now();
    setToasts((t) => [...t, { id, message, variant }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);

  return (
    <ToastCtx.Provider value={{ add }}>
      {children}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={
              'px-3 py-2 rounded shadow text-white ' +
              (t.variant === 'error' ? 'bg-red-600' : t.variant === 'success' ? 'bg-green-600' : 'bg-gray-800')
            }
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

