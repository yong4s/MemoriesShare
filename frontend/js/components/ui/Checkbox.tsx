import React from 'react';

interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, className = '', id, ...props }, ref) => {
    const checkboxId = id ?? label.toLowerCase().replace(/\s+/g, '-');

    return (
      <label htmlFor={checkboxId} className={`flex cursor-pointer items-start gap-2.5 ${className}`}>
        <input
          ref={ref}
          id={checkboxId}
          type="checkbox"
          className="mt-0.5 h-4 w-4 rounded border-border-strong bg-surface-1 text-brand-500 transition focus:ring-2 focus:ring-brand-400 focus:ring-offset-1 focus:ring-offset-surface"
          {...props}
        />
        <div>
          <span className="text-sm font-medium text-ink">{label}</span>
          {description && <p className="text-xs text-ink-muted">{description}</p>}
        </div>
      </label>
    );
  },
);

Checkbox.displayName = 'Checkbox';

export default Checkbox;
