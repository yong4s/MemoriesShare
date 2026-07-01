import { format, isValid, parse, startOfDay } from 'date-fns';
import { Calendar } from 'lucide-react';
import React, { useMemo, useState } from 'react';
import { DayPicker } from 'react-day-picker';

import Popover from './Popover';

import 'react-day-picker/style.css';

interface DatePickerFieldProps {
  label: string;
  /** Stored as YYYY-MM-DD string (matches backend `date` field). `null` or '' = empty. */
  value: string | null;
  onChange: (value: string) => void;
  error?: string;
  /** YYYY-MM-DD; selections before this are disabled. Defaults to today. */
  min?: string;
  required?: boolean;
  placeholder?: string;
  id?: string;
  onBlur?: () => void;
}

const DATE_FMT = 'yyyy-MM-dd';
const DISPLAY_FMT = 'EEE, d MMM yyyy';

const parseISODate = (value: string | null | undefined): Date | undefined => {
  if (!value) return undefined;
  const parsed = parse(value, DATE_FMT, new Date());
  return isValid(parsed) ? parsed : undefined;
};

const DatePickerField: React.FC<DatePickerFieldProps> = ({
  label,
  value,
  onChange,
  error,
  min,
  required = false,
  placeholder = 'Pick a date',
  id,
  onBlur,
}) => {
  const [open, setOpen] = useState(false);
  const generatedId = React.useId();
  const fieldId = id ?? `datepicker-${generatedId}`;

  const selected = useMemo(() => parseISODate(value), [value]);
  const minDate = useMemo(() => parseISODate(min) ?? startOfDay(new Date()), [min]);

  const displayValue = selected ? format(selected, DISPLAY_FMT) : '';

  const handleSelect = (date: Date | undefined) => {
    if (date) {
      onChange(format(date, DATE_FMT));
      setOpen(false);
    }
  };

  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
        {required && <span className="ml-0.5 text-blush-500">*</span>}
      </label>
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) onBlur?.();
        }}
        trigger={
          <button
            type="button"
            id={fieldId}
            aria-haspopup="dialog"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className={[
              'relative flex w-full items-center justify-between gap-2 rounded-xl border bg-surface-1 px-3 py-2 text-left text-sm transition-all duration-150',
              'focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30',
              error ? 'border-blush-500' : 'border-border-subtle',
              displayValue ? 'text-ink' : 'text-ink-faint',
            ].join(' ')}
          >
            <span>{displayValue || placeholder}</span>
            <Calendar className="h-4 w-4 text-ink-faint" />
          </button>
        }
      >
        <DayPicker
          mode="single"
          selected={selected}
          onSelect={handleSelect}
          disabled={{ before: minDate }}
          showOutsideDays
          weekStartsOn={1}
          classNames={{
            root: 'rdp-root text-sm text-ink',
            months: 'flex flex-col gap-2',
            month_caption: 'flex items-center justify-between px-2 py-1 font-medium text-ink',
            caption_label: 'font-medium',
            nav: 'flex items-center gap-1',
            button_previous:
              'inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-muted hover:bg-surface-2 hover:text-ink',
            button_next:
              'inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-muted hover:bg-surface-2 hover:text-ink',
            month_grid: 'border-collapse',
            weekdays: 'flex',
            weekday: 'h-8 w-9 text-center text-xs font-medium text-ink-faint',
            week: 'flex',
            day: 'h-9 w-9 text-center',
            day_button:
              'inline-flex h-9 w-9 items-center justify-center rounded-md text-sm hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400',
            today: 'font-semibold text-brand-500',
            selected: '[&_.rdp-day_button]:bg-brand-500 [&_.rdp-day_button]:text-white [&_.rdp-day_button]:hover:bg-brand-600',
            outside: 'text-ink-faint',
            disabled: 'text-ink-faint opacity-40 cursor-not-allowed',
          }}
        />
      </Popover>
      {error && <p className="mt-1 text-xs text-blush-700">{error}</p>}
    </div>
  );
};

export default DatePickerField;
