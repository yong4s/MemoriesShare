import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const textareaId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className={className}>
        {label && (
          <label htmlFor={textareaId} className="mb-1.5 block text-sm font-medium text-ink">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={[
            'min-h-24 w-full rounded-xl border bg-surface-1 p-3 text-sm text-ink',
            'transition-all duration-150 placeholder:text-ink-faint',
            'focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30',
            'disabled:cursor-not-allowed disabled:bg-surface-2',
            error ? 'border-crimson-500' : 'border-border-subtle',
          ].join(' ')}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-crimson-700">{error}</p>}
      </div>
    );
  },
);

Textarea.displayName = 'Textarea';

export default Textarea;
