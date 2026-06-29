import { UserPlus } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import Badge from './ui/Badge';
import Button from './ui/Button';
import Card from './ui/Card';

import { EventParticipantListItem, listEventParticipants } from '@/js/api';
import { extractBackendErrorMessage } from '@/js/utils';

type BadgeVariant = 'owner' | 'moderator' | 'guest' | 'accepted' | 'declined' | 'pending' | 'maybe';

interface ParticipantListProps {
  eventUuid: string;
  canModify: boolean;
  showEmails: boolean;
  onInviteClick?: () => void;
}

const roleBadgeVariant = (role: string): BadgeVariant => {
  const lower = role.toLowerCase();
  if (lower === 'owner') return 'owner';
  if (lower === 'moderator') return 'moderator';
  return 'guest';
};

const rsvpBadgeVariant = (status: string): BadgeVariant => {
  const lower = status.toLowerCase();
  if (lower === 'accepted' || lower === 'attending') return 'accepted';
  if (lower === 'declined' || lower === 'not_attending') return 'declined';
  if (lower === 'maybe') return 'maybe';
  return 'pending';
};

const AVATAR_COLORS = [
  'bg-brand-100 text-brand-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-sky-100 text-sky-700',
  'bg-violet-100 text-violet-700',
  'bg-rose-100 text-rose-700',
];

const getAvatarColor = (index: number): string => AVATAR_COLORS[index % AVATAR_COLORS.length];

const ParticipantList = ({ eventUuid, canModify, showEmails, onInviteClick }: ParticipantListProps) => {
  const [participants, setParticipants] = useState<EventParticipantListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const loadParticipants = async () => {
      try {
        const response = await listEventParticipants(eventUuid);
        const data = response.data;
        setParticipants(data.participants ?? (data as unknown as EventParticipantListItem[]) ?? []);
      } catch (error) {
        setErrorMessage(extractBackendErrorMessage(error, 'Failed to load participants.'));
      } finally {
        setIsLoading(false);
      }
    };

    loadParticipants();
  }, [eventUuid]);

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">
          Participants
          {!isLoading && participants.length > 0 && (
            <span className="ml-2 text-sm font-normal text-zinc-400">({participants.length})</span>
          )}
        </h3>
        {canModify && onInviteClick && (
          <Button size="sm" onClick={onInviteClick} icon={<UserPlus className="h-4 w-4" />}>
            Invite
          </Button>
        )}
      </div>

      {isLoading && <p className="text-sm text-zinc-500">Loading participants...</p>}
      {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}

      {!isLoading && !errorMessage && participants.length === 0 && (
        <p className="text-sm text-zinc-500">No participants yet.</p>
      )}

      {!isLoading && !errorMessage && participants.length > 0 && (
        <div className="divide-y divide-zinc-100">
          {participants.map((participant, index) => {
            const name = participant.user_name || participant.guest_name || 'Unknown';
            const initial = name[0]?.toUpperCase() ?? '?';

            return (
              <div key={participant.id} className="flex items-center justify-between py-2.5 transition-colors hover:bg-zinc-50 -mx-4 px-4 first:-mt-1 last:-mb-1">
                <div className="flex items-center gap-3">
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${getAvatarColor(index)}`}>
                    {initial}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800">{name}</p>
                    {showEmails && participant.is_registered_user && (
                      <p className="text-xs text-zinc-400">{participant.guest_name}</p>
                    )}
                  </div>
                </div>
                <div className="flex gap-1.5">
                  <Badge variant={roleBadgeVariant(participant.role)}>{participant.role}</Badge>
                  <Badge variant={rsvpBadgeVariant(participant.rsvp_status)}>{participant.rsvp_status}</Badge>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};

export default ParticipantList;
