import React from 'react';

interface PageLayoutProps {
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
  children: React.ReactNode;
  className?: string;
}

const maxWidthStyles: Record<string, string> = {
  sm: 'max-w-2xl',
  md: 'max-w-3xl',
  lg: 'max-w-4xl',
  xl: 'max-w-6xl',
};

const PageLayout = ({ maxWidth = 'lg', children, className = '' }: PageLayoutProps) => (
  <main
    className={[
      'animate-fade-in mx-auto px-4 pb-12',
      maxWidthStyles[maxWidth],
      className,
    ].join(' ')}
  >
    {children}
  </main>
);

export default PageLayout;
