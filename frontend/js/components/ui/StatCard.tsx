import React from 'react';

interface StatCardProps {
  label: string;
  value: number | string;
  icon?: React.ReactNode;
  accent?: 'brand' | 'peach' | 'sage' | 'crimson' | 'butter';
}

const accentStyles: Record<NonNullable<StatCardProps['accent']>, string> = {
  brand: 'text-brand-500',
  peach: 'text-peach-500',
  sage: 'text-sage-500',
  crimson: 'text-crimson-500',
  butter: 'text-butter-700',
};

const StatCard = ({ label, value, icon, accent = 'brand' }: StatCardProps) => (
  <div className="group rounded-2xl bg-surface-1/60 px-5 py-4 transition-colors duration-200 hover:bg-surface-1">
    <div className="flex items-center justify-between">
      <p className="text-xs font-medium uppercase tracking-wider text-ink-faint">{label}</p>
      {icon && <span className={`shrink-0 ${accentStyles[accent]}`}>{icon}</span>}
    </div>
    <p className="mt-2 text-4xl font-semibold tracking-tight tabular-nums text-ink">{value}</p>
  </div>
);

export default StatCard;
