import { Check, Clock, Crown, Globe, HelpCircle, Lock, Shield, User, X } from 'lucide-react';
import React from 'react';

type BadgeVariant =
  | 'owner'
  | 'guest'
  | 'moderator'
  | 'accepted'
  | 'declined'
  | 'pending'
  | 'maybe'
  | 'public'
  | 'private';

interface BadgeProps {
  variant: BadgeVariant;
  children?: React.ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
  owner: 'bg-brand-100 text-brand-700 ring-1 ring-brand-200',
  moderator: 'bg-peach-100 text-peach-700 ring-1 ring-peach-300/60',
  guest: 'bg-surface-2 text-ink-muted ring-1 ring-border-subtle',
  accepted: 'bg-sage-100 text-sage-700 ring-1 ring-sage-300/60',
  declined: 'bg-crimson-100 text-crimson-700 ring-1 ring-crimson-300/60',
  pending: 'bg-butter-100 text-butter-700 ring-1 ring-butter-300/60',
  maybe: 'bg-brand-50 text-brand-600 ring-1 ring-brand-200',
  public: 'bg-sage-100 text-sage-700 ring-1 ring-sage-300/60',
  private: 'bg-surface-2 text-ink-muted ring-1 ring-border-subtle',
};

const variantIcons: Record<BadgeVariant, React.ReactNode> = {
  owner: <Crown className="h-3 w-3" />,
  moderator: <Shield className="h-3 w-3" />,
  guest: <User className="h-3 w-3" />,
  accepted: <Check className="h-3 w-3" />,
  declined: <X className="h-3 w-3" />,
  pending: <Clock className="h-3 w-3" />,
  maybe: <HelpCircle className="h-3 w-3" />,
  public: <Globe className="h-3 w-3" />,
  private: <Lock className="h-3 w-3" />,
};

const defaultLabels: Record<BadgeVariant, string> = {
  owner: 'Owner',
  moderator: 'Moderator',
  guest: 'Participant',
  accepted: 'Accepted',
  declined: 'Declined',
  pending: 'Pending',
  maybe: 'Maybe',
  public: 'Public',
  private: 'Private',
};

const Badge = ({ variant, children }: BadgeProps) => (
  <span
    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${variantStyles[variant]}`}
  >
    {variantIcons[variant]}
    {children ?? defaultLabels[variant]}
  </span>
);

export default Badge;
