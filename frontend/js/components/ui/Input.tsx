import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  icon?: React.ReactNode;
  error?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, icon, error, className = '', id, ...props }, ref) => {
    const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className={className}>
        {label && (
          <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={[
              'w-full rounded-xl border bg-surface-1 px-3 py-2 text-sm text-ink',
              'transition-all duration-150 placeholder:text-ink-faint',
              'focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30',
              'disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-ink-faint',
              icon ? 'pl-10' : '',
              error ? 'border-blush-500' : 'border-border-subtle',
            ].join(' ')}
            {...props}
          />
        </div>
        {error && <p className="mt-1 text-xs text-blush-700">{error}</p>}
      </div>
    );
  },
);

Input.displayName = 'Input';

export default Input;
