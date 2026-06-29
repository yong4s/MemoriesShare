import { Clock, Minus, Plus } from 'lucide-react';
import React, { useState } from 'react';

import Popover from './Popover';

interface TimePickerFieldProps {
  label: string;
  /** HH:MM (24h). Empty string when unset. */
  value: string;
  onChange: (value: string) => void;
  error?: string;
  /** Renders a collapsed placeholder instead of the field. Used for all_day flow. */
  hidden?: boolean;
  hiddenHelper?: string;
  id?: string;
  onBlur?: () => void;
}

const PRESETS: ReadonlyArray<{ label: string; value: string }> = [
  { label: '12:00', value: '12:00' },
  { label: '17:00', value: '17:00' },
  { label: '18:00', value: '18:00' },
  { label: '19:00', value: '19:00' },
  { label: '20:00', value: '20:00' },
];

const stepTime = (current: string, deltaMin: number): string => {
  const [h, m] = (current || '18:00').split(':').map(Number);
  let total = h * 60 + m + deltaMin;
  total = ((total % (24 * 60)) + 24 * 60) % (24 * 60);
  const nh = Math.floor(total / 60);
  const nm = total % 60;
  return `${String(nh).padStart(2, '0')}:${String(nm).padStart(2, '0')}`;
};

const TimePickerField: React.FC<TimePickerFieldProps> = ({
  label,
  value,
  onChange,
  error,
  hidden = false,
  hiddenHelper,
  id,
  onBlur,
}) => {
  const [open, setOpen] = useState(false);
  const generatedId = React.useId();
  const fieldId = id ?? `timepicker-${generatedId}`;

  if (hidden) {
    return (
      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink-faint">{label}</label>
        <div className="rounded-xl border border-dashed border-border-subtle bg-surface-2 px-3 py-2 text-xs text-ink-muted">
          {hiddenHelper ?? 'Time hidden — event runs all day.'}
        </div>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          id={fieldId}
          type="time"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={[
            'w-full rounded-xl border bg-surface-1 px-3 py-2 text-sm text-ink',
            'transition-all duration-150 placeholder:text-ink-faint',
            'focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30',
            error ? 'border-blush-500' : 'border-border-subtle',
          ].join(' ')}
        />
        <Popover
          open={open}
          onOpenChange={setOpen}
          trigger={
            <button
              type="button"
              aria-haspopup="dialog"
              aria-expanded={open}
              aria-label="Pick time preset"
              onClick={() => setOpen((o) => !o)}
              className="inline-flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-xl border border-border-subtle bg-surface-1 text-ink-muted transition hover:bg-surface-2 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <Clock className="h-4 w-4" />
            </button>
          }
          panelClassName="sm:p-3 sm:min-w-56"
        >
          <div className="space-y-3">
            <div>
              <p className="mb-1.5 px-1 text-xs font-medium text-ink-muted">Quick picks</p>
              <div className="flex flex-wrap gap-1.5">
                {PRESETS.map((preset) => {
                  const active = value === preset.value;
                  return (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => {
                        onChange(preset.value);
                        setOpen(false);
                      }}
                      className={[
                        'rounded-lg border px-2.5 py-1 text-xs font-medium transition',
                        active
                          ? 'border-brand-500 bg-brand-500 text-white'
                          : 'border-border-subtle bg-surface-1 text-ink hover:bg-surface-2',
                      ].join(' ')}
                    >
                      {preset.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <p className="mb-1.5 px-1 text-xs font-medium text-ink-muted">Adjust</p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onChange(stepTime(value, -15))}
                  className="inline-flex items-center gap-1 rounded-lg border border-border-subtle bg-surface-1 px-2 py-1 text-xs text-ink hover:bg-surface-2"
                  aria-label="Subtract 15 minutes"
                >
                  <Minus className="h-3 w-3" /> 15m
                </button>
                <button
                  type="button"
                  onClick={() => onChange(stepTime(value, 15))}
                  className="inline-flex items-center gap-1 rounded-lg border border-border-subtle bg-surface-1 px-2 py-1 text-xs text-ink hover:bg-surface-2"
                  aria-label="Add 15 minutes"
                >
                  <Plus className="h-3 w-3" /> 15m
                </button>
              </div>
            </div>
          </div>
        </Popover>
      </div>
      {error && <p className="mt-1 text-xs text-blush-700">{error}</p>}
    </div>
  );
};

export default TimePickerField;
