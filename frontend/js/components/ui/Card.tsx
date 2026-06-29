import React from 'react';

type CardPadding = 'sm' | 'md' | 'lg';
type CardVariant = 'solid' | 'glass' | 'tinted';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: CardPadding;
  variant?: CardVariant;
}

const paddingStyles: Record<CardPadding, string> = {
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

const variantStyles: Record<CardVariant, string> = {
  solid: 'border border-border-subtle bg-surface-1 shadow-soft-sm',
  glass: 'glass shadow-soft-sm',
  tinted: 'border border-border-subtle bg-surface-2 shadow-soft-sm',
};

const Card = ({
  children,
  className = '',
  hover = false,
  padding = 'md',
  variant = 'solid',
}: CardProps) => (
  <div
    className={[
      'rounded-2xl',
      variantStyles[variant],
      paddingStyles[padding],
      hover
        ? 'transition-all duration-300 hover:border-border-strong hover:shadow-soft-lg hover:-translate-y-0.5'
        : '',
      className,
    ].join(' ')}
  >
    {children}
  </div>
);

export default Card;
