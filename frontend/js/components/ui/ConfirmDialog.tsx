import { AlertTriangle, Info } from 'lucide-react';
import React from 'react';

import Button from './Button';

type ConfirmDialogVariant = 'danger' | 'primary';

interface ConfirmDialogProps {
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmDialogVariant;
  isLoading?: boolean;
}

const ConfirmDialog = ({
  title,
  message,
  onConfirm,
  onCancel,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  isLoading = false,
}: ConfirmDialogProps) => (
  <div
    className="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-md"
    onClick={onCancel}
  >
    <div
      className="animate-slide-up glass-strong w-full max-w-md rounded-2xl p-6 shadow-soft-lg"
      onClick={(event) => event.stopPropagation()}
    >
      <div className="mb-4 flex items-start gap-3">
        <div
          className={`shrink-0 rounded-xl p-2.5 ${
            variant === 'danger'
              ? 'bg-blush-100 text-blush-700'
              : 'bg-brand-100 text-brand-700'
          }`}
        >
          {variant === 'danger' ? <AlertTriangle className="h-5 w-5" /> : <Info className="h-5 w-5" />}
        </div>
        <div>
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm text-ink-muted">{message}</p>
        </div>
      </div>
      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={onCancel} disabled={isLoading}>
          {cancelLabel}
        </Button>
        <Button
          variant={variant === 'danger' ? 'danger' : 'primary'}
          onClick={onConfirm}
          isLoading={isLoading}
        >
          {confirmLabel}
        </Button>
      </div>
    </div>
  </div>
);

export default ConfirmDialog;
