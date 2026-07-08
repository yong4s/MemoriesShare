import { Loader2 } from 'lucide-react';
import React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'soft';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  icon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: [
    'bg-gradient-to-r from-brand-600 to-brand-700 text-white',
    'hover:from-brand-700 hover:to-brand-800 hover:shadow-soft-md hover:-translate-y-px',
    'active:translate-y-0 active:shadow-soft-sm',
    'disabled:from-brand-300 disabled:to-brand-400 disabled:shadow-none disabled:hover:translate-y-0',
    'shadow-soft-sm',
  ].join(' '),
  secondary: [
    'border border-border-subtle bg-surface-1 text-ink',
    'hover:bg-surface-2 hover:border-border-strong active:bg-surface-3',
    'disabled:opacity-60 shadow-soft-sm',
  ].join(' '),
  danger: [
    'bg-gradient-to-r from-crimson-500 to-crimson-700 text-white',
    'hover:shadow-soft-md hover:-translate-y-px active:translate-y-0',
    'disabled:from-crimson-300 disabled:to-crimson-300 disabled:shadow-none',
    'shadow-soft-sm',
  ].join(' '),
  ghost: 'text-ink-muted hover:bg-surface-2 hover:text-ink disabled:opacity-60',
  soft: [
    'bg-brand-100 text-brand-700',
    'hover:bg-brand-200 active:bg-brand-300',
    'disabled:opacity-60 shadow-soft-sm',
  ].join(' '),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-5 py-2.5 text-base gap-2',
};

const Button = ({ variant = 'primary', size = 'md', isLoading, icon, children, disabled, className = '', ...props }: ButtonProps) => (
  <button
    className={[
      'group inline-flex items-center justify-center rounded-xl font-medium',
      'transition-all duration-200 focus-visible:outline-none',
      'focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
      'disabled:cursor-not-allowed',
      variantStyles[variant],
      sizeStyles[size],
      className,
    ].join(' ')}
    disabled={disabled || isLoading}
    type="button"
    {...props}
  >
    {isLoading ? (
      <>
        <Loader2 className="h-4 w-4 animate-spin" />
        {children}
      </>
    ) : (
      <>
        {icon && <span className="shrink-0 transition-transform duration-200 group-hover:scale-110">{icon}</span>}
        {children}
      </>
    )}
  </button>
);

export default Button;
