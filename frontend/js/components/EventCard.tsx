import { Calendar, Clock, MapPin, Users } from 'lucide-react';
import React from 'react';
import { Link } from 'react-router';

import Badge from './ui/Badge';

import type { EventListItem } from '@/js/api';

import { formatDate, formatTime } from '@/js/utils';

interface EventCardProps {
  event: EventListItem;
  isOwner: boolean;
}

const EventCard = ({ event, isOwner }: EventCardProps) => (
  <Link
    className="group relative block rounded-2xl px-5 py-4.5 transition-colors duration-200 hover:bg-surface-1"
    to={`/events/${event.event_uuid}`}
  >
    {isOwner && (
      <span
        aria-hidden
        className="absolute left-0 top-5 bottom-5 w-0.5 rounded-full bg-brand-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
      />
    )}

    <div className="flex items-start justify-between gap-3">
      <h2 className="text-xl font-semibold leading-snug tracking-tight text-ink decoration-brand-400/40 decoration-2 underline-offset-4 group-hover:underline">
        {event.event_name}
      </h2>
      <div className="flex shrink-0 gap-1.5 pt-1">
        <Badge variant={isOwner ? 'owner' : 'guest'} />
        <Badge variant={event.is_public ? 'public' : 'private'} />
      </div>
    </div>

    <div className="mt-3 h-px bg-border-subtle" />

    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-ink-muted">
      <span className="flex items-center gap-1.5">
        <Calendar className="h-4 w-4 text-ink-faint" />
        {formatDate(event.date)}
      </span>
      <span aria-hidden className="text-ink-faint/50">&middot;</span>
      <span className="flex items-center gap-1.5">
        <Clock className="h-4 w-4 text-ink-faint" />
        {formatTime(event.time)}
      </span>
      {event.location && (
        <>
          <span aria-hidden className="text-ink-faint/50">&middot;</span>
          <span className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4 text-ink-faint" />
            {event.location}
          </span>
        </>
      )}
    </div>

    <div className="mt-3 flex items-center justify-between text-xs text-ink-faint">
      <span className="flex items-center gap-1.5">
        <Users className="h-3.5 w-3.5" />
        <span className="font-medium text-ink-muted">{event.total_participants}</span>
        {event.total_participants !== 1 ? ' participants' : ' participant'}
        <span aria-hidden className="text-ink-faint/50">&middot;</span>
        <span className="font-medium text-ink-muted">{event.attending_count}</span> going
      </span>
      <span>by {event.owner_name}</span>
    </div>
  </Link>
);

export default EventCard;
