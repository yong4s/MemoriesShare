import { Loader2 } from 'lucide-react';
import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
}

const LoadingSpinner = ({ message = 'Loading...' }: LoadingSpinnerProps) => (
  <div className="animate-fade-in flex flex-col items-center justify-center py-14">
    <div className="relative">
      <div className="absolute inset-0 animate-pulse-soft rounded-full bg-gradient-to-br from-brand-300 to-brand-500 blur-xl" />
      <Loader2 className="relative h-9 w-9 animate-spin text-brand-500" strokeWidth={2.2} />
    </div>
    <p className="mt-4 text-sm text-ink-muted">{message}</p>
  </div>
);

export default LoadingSpinner;
