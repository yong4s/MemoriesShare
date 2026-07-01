import React from 'react';

interface StatCardProps {
  label: string;
  value: number | string;
  icon?: React.ReactNode;
  accent?: 'brand' | 'peach' | 'sage' | 'blush' | 'butter';
}

const accentStyles: Record<NonNullable<StatCardProps['accent']>, { bar: string; icon: string }> = {
  brand: { bar: 'from-brand-400 to-brand-500', icon: 'text-brand-500' },
  peach: { bar: 'from-peach-300 to-peach-500', icon: 'text-peach-500' },
  sage: { bar: 'from-sage-300 to-sage-500', icon: 'text-sage-500' },
  blush: { bar: 'from-blush-300 to-blush-500', icon: 'text-blush-500' },
  butter: { bar: 'from-butter-300 to-butter-500', icon: 'text-butter-700' },
};

const StatCard = ({ label, value, icon, accent = 'brand' }: StatCardProps) => {
  const styles = accentStyles[accent];
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-border-subtle bg-surface-1 p-5 text-center shadow-soft-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-soft-md">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${styles.bar}`} />
      {icon && (
        <div
          className={`mb-2 flex justify-center transition-transform duration-300 group-hover:scale-110 ${styles.icon}`}
        >
          {icon}
        </div>
      )}
      <p className="text-3xl font-bold tracking-tight text-ink">{value}</p>
      <p className="mt-1 text-xs font-medium uppercase tracking-wider text-ink-faint">{label}</p>
    </div>
  );
};

export default StatCard;
