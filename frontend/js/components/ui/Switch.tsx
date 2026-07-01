import React from 'react';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
}

/**
 * Accessible toggle switch. Use when flipping the value reveals/hides other UI
 * (e.g. all_day → hides Time field) or for prominent on/off settings.
 * For passive multi-select choices prefer Checkbox.
 */
const Switch: React.FC<SwitchProps> = ({ checked, onChange, label, description, disabled = false, className = '', id }) => {
  const generatedId = React.useId();
  const switchId = id ?? `switch-${generatedId}`;
  const labelId = `${switchId}-label`;
  const descId = description ? `${switchId}-desc` : undefined;

  return (
    <div className={`flex items-start gap-3 ${className}`}>
      <button
        type="button"
        role="switch"
        id={switchId}
        aria-checked={checked}
        aria-labelledby={labelId}
        aria-describedby={descId}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
          'disabled:cursor-not-allowed disabled:opacity-50',
          checked ? 'bg-brand-500' : 'bg-surface-3',
        ].join(' ')}
      >
        <span
          aria-hidden="true"
          className={[
            'inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200',
            checked ? 'translate-x-[22px]' : 'translate-x-0.5',
          ].join(' ')}
        />
      </button>
      <div className="flex-1">
        <label
          id={labelId}
          htmlFor={switchId}
          className={`block text-sm font-medium text-ink ${disabled ? 'opacity-60' : 'cursor-pointer'}`}
        >
          {label}
        </label>
        {description && (
          <p id={descId} className="text-xs text-ink-muted">
            {description}
          </p>
        )}
      </div>
    </div>
  );
};

export default Switch;
