import React, { useEffect, useRef } from 'react';

interface PopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trigger: React.ReactNode;
  children: React.ReactNode;
  /** Optional class for the panel; merged with the default container styling. */
  panelClassName?: string;
  /** Used by trigger (`aria-controls`) to point at the panel. Auto-generated if omitted. */
  panelId?: string;
}

/**
 * Lightweight anchored popover. Uses native focus management — the trigger
 * keeps focus when closed, the panel children manage their own focus when open.
 * On <sm viewport, the panel renders as a bottom sheet.
 */
const Popover: React.FC<PopoverProps> = ({ open, onOpenChange, trigger, children, panelClassName = '', panelId }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const generatedId = React.useId();
  const id = panelId ?? `popover-${generatedId}`;

  useEffect(() => {
    if (!open) return undefined;

    const onMouseDown = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        onOpenChange(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onOpenChange(false);
        const focusable = triggerRef.current?.querySelector<HTMLElement>('button, [href], input, [tabindex]:not([tabindex="-1"])');
        focusable?.focus();
      }
    };

    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, onOpenChange]);

  return (
    <div ref={containerRef} className="relative">
      <div ref={triggerRef}>{trigger}</div>
      {open && (
        <>
          {/* Mobile backdrop — only visible <sm */}
          <div
            className="fixed inset-0 z-40 bg-ink/30 backdrop-blur-sm sm:hidden"
            aria-hidden="true"
            onMouseDown={() => onOpenChange(false)}
          />
          <div
            id={id}
            role="dialog"
            className={[
              // Mobile: full-width bottom sheet
              'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl border border-border-subtle bg-surface-1 p-3 shadow-lg',
              // Desktop: anchored dropdown
              'sm:absolute sm:inset-x-auto sm:bottom-auto sm:left-0 sm:top-full sm:mt-2 sm:w-auto sm:rounded-xl',
              'animate-fade-in',
              panelClassName,
            ].join(' ')}
          >
            {children}
          </div>
        </>
      )}
    </div>
  );
};

export default Popover;
