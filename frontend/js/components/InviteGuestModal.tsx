import { UserPlus, X } from 'lucide-react';
import React, { FormEvent, useState } from 'react';

import { Alert, Button, Input } from './ui';

import { inviteGuest } from '@/js/api';
import { extractBackendErrorMessage } from '@/js/utils';

interface InviteGuestModalProps {
  eventUuid: string;
  onClose: () => void;
  onInvited: () => void;
}

const InviteGuestModal = ({ eventUuid, onClose, onInvited }: InviteGuestModalProps) => {
  const [guestName, setGuestName] = useState('');
  const [guestEmail, setGuestEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onSubmit = async (formEvent: FormEvent<HTMLFormElement>) => {
    formEvent.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      await inviteGuest(eventUuid, {
        guest_name: guestName.trim(),
        guest_email: guestEmail.trim() || undefined,
      });
      onInvited();
      onClose();
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to invite guest.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-ink/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="animate-slide-up w-full max-w-md rounded-2xl border border-border-subtle bg-surface-1 p-6 shadow-soft-lg"
        onClick={(clickEvent) => clickEvent.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <UserPlus className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold text-ink">Invite Guest</h2>
          </div>
          <button className="rounded-lg p-1.5 text-ink-faint transition hover:bg-surface-2 hover:text-ink" type="button" onClick={onClose}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mb-3">
            <Alert variant="error">{errorMessage}</Alert>
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            label="Guest name"
            required
            type="text"
            value={guestName}
            onChange={(e) => setGuestName(e.target.value)}
            placeholder="John Doe"
          />

          <Input
            label="Guest email (optional)"
            type="email"
            value={guestEmail}
            onChange={(e) => setGuestEmail(e.target.value)}
            placeholder="john@example.com"
          />

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoading} disabled={!guestName.trim()} icon={<UserPlus className="h-4 w-4" />}>
              Send Invite
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default InviteGuestModal;
