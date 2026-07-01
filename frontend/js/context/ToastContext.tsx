import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import React, { createContext, useCallback, useContext, useState } from 'react';

type ToastVariant = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  variant: ToastVariant;
  message: string;
}

interface ToastContextValue {
  toast: {
    success: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
  };
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_DURATION = 4000;
let toastId = 0;

const variantStyles: Record<ToastVariant, string> = {
  success: 'border-sage-300/60 bg-sage-100/90 text-sage-700',
  error: 'border-crimson-300/60 bg-crimson-100/90 text-crimson-700',
  info: 'border-brand-200 bg-brand-50 text-brand-700',
};

const variantIcons: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle className="h-5 w-5 text-sage-500" />,
  error: <AlertCircle className="h-5 w-5 text-crimson-500" />,
  info: <Info className="h-5 w-5 text-brand-500" />,
};

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((variant: ToastVariant, message: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, variant, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, TOAST_DURATION);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = {
    success: (message: string) => addToast('success', message),
    error: (message: string) => addToast('error', message),
    info: (message: string) => addToast('info', message),
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`animate-toast-in flex items-start gap-2.5 rounded-xl border p-3.5 shadow-soft-lg backdrop-blur-md ${variantStyles[t.variant]}`}
            style={{ minWidth: 280, maxWidth: 400 }}
          >
            <span className="shrink-0 mt-0.5">{variantIcons[t.variant]}</span>
            <p className="flex-1 text-sm font-medium">{t.message}</p>
            <button className="shrink-0 rounded-md p-0.5 opacity-60 hover:opacity-100 transition-opacity" type="button" onClick={() => removeToast(t.id)}>
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextValue['toast'] => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx.toast;
};
