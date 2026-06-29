import { Moon, Sun } from 'lucide-react';
import React from 'react';

import { useTheme } from '@/js/context/ThemeContext';

interface ThemeToggleProps {
  className?: string;
}

const ThemeToggle = ({ className = '' }: ThemeToggleProps) => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      aria-pressed={isDark}
      className={[
        'relative inline-flex h-9 w-9 items-center justify-center rounded-full',
        'border border-border-subtle bg-surface-1/70 backdrop-blur-sm',
        'text-ink-muted hover:text-brand-500 hover:border-border-strong',
        'transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
        className,
      ].join(' ')}
      title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      type="button"
      onClick={toggleTheme}
    >
      <Sun
        className={[
          'absolute h-4.5 w-4.5 transition-all duration-300',
          isDark ? 'scale-0 rotate-90 opacity-0' : 'scale-100 rotate-0 opacity-100',
        ].join(' ')}
      />
      <Moon
        className={[
          'absolute h-4.5 w-4.5 transition-all duration-300',
          isDark ? 'scale-100 rotate-0 opacity-100' : 'scale-0 -rotate-90 opacity-0',
        ].join(' ')}
      />
    </button>
  );
};

export default ThemeToggle;
