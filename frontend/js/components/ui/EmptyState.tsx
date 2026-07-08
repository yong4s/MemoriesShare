import { Inbox } from 'lucide-react';
import React from 'react';

import Button from './Button';

interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

interface EmptyStateProps {
  title: string;
  message?: string;
  action?: EmptyStateAction;
  icon?: React.ReactNode;
}

const EmptyState = ({ title, message, action, icon }: EmptyStateProps) => (
  <div className="animate-fade-in flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-strong bg-surface-1/40 py-14 text-center">
    <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100 text-brand-600 shadow-soft-sm">
      {icon ?? <Inbox className="h-7 w-7" />}
    </div>
    <h3 className="text-lg font-semibold text-ink">{title}</h3>
    {message && <p className="mt-1 max-w-sm text-sm text-ink-muted">{message}</p>}
    {action && (
      <div className="mt-5">
        <Button onClick={action.onClick}>{action.label}</Button>
      </div>
    )}
  </div>
);

export default EmptyState;
