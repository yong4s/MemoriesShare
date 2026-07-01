import React from 'react';

import Button from './Button';

interface PageHeaderAction {
  label: string;
  onClick: () => void;
  icon?: React.ReactNode;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: PageHeaderAction;
}

const PageHeader = ({ title, subtitle, action }: PageHeaderProps) => (
  <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-5">
    <div>
      <h1 className="bg-gradient-to-r from-ink to-ink-muted bg-clip-text text-3xl font-bold tracking-tight text-transparent">
        {title}
      </h1>
      {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
    </div>
    {action && (
      <Button icon={action.icon} onClick={action.onClick}>
        {action.label}
      </Button>
    )}
  </div>
);

export default PageHeader;
