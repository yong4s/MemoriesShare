import React from 'react';

interface FormSectionProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  /** First section in a form skips the top divider. */
  first?: boolean;
  className?: string;
}

const FormSection: React.FC<FormSectionProps> = ({ title, subtitle, children, first = false, className = '' }) => (
  <section
    className={[
      first ? '' : 'mt-6 border-t border-border-subtle pt-6',
      className,
    ].join(' ')}
  >
    <header className="mb-4">
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {subtitle && <p className="mt-0.5 text-xs text-ink-muted">{subtitle}</p>}
    </header>
    <div className="space-y-4">{children}</div>
  </section>
);

export default FormSection;
