import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from 'lucide-react';
import React from 'react';

type AlertVariant = 'error' | 'success' | 'warning' | 'info';

interface AlertProps {
  variant: AlertVariant;
  children: React.ReactNode;
  onDismiss?: () => void;
}

const variantStyles: Record<AlertVariant, string> = {
  error: 'border-crimson-300/60 bg-crimson-100/70 text-crimson-700',
  success: 'border-sage-300/60 bg-sage-100/70 text-sage-700',
  warning: 'border-butter-300/60 bg-butter-100/70 text-butter-700',
  info: 'border-brand-200/80 bg-brand-50 text-brand-700',
};

const variantIcons: Record<AlertVariant, React.ReactNode> = {
  error: <AlertCircle className="h-5 w-5 shrink-0 text-crimson-500" />,
  success: <CheckCircle className="h-5 w-5 shrink-0 text-sage-500" />,
  warning: <AlertTriangle className="h-5 w-5 shrink-0 text-butter-500" />,
  info: <Info className="h-5 w-5 shrink-0 text-brand-500" />,
};

const Alert = ({ variant, children, onDismiss }: AlertProps) => (
  <div
    className={`animate-fade-in rounded-xl border p-3.5 text-sm shadow-soft-sm ${variantStyles[variant]}`}
    role="alert"
  >
    <div className="flex items-start gap-2.5">
      {variantIcons[variant]}
      <div className="flex-1 pt-0.5">{children}</div>
      {onDismiss && (
        <button
          aria-label="Dismiss"
          className="shrink-0 rounded-md p-0.5 opacity-60 transition-opacity hover:opacity-100"
          type="button"
          onClick={onDismiss}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  </div>
);

export default Alert;
