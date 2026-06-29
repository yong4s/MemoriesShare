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
    className={`block rounded-xl border bg-white p-4 shadow-sm transition-all duration-200 hover:shadow-md hover:scale-[1.01] ${isOwner ? 'border-l-4 border-l-brand-500 border-zinc-200' : 'border-zinc-200'}`}
    to={`/events/${event.event_uuid}`}
  >
    <div className="flex items-start justify-between gap-2">
      <h2 className="text-lg font-semibold text-slate-900">{event.event_name}</h2>
      <div className="flex shrink-0 gap-1.5">
        <Badge variant={isOwner ? 'owner' : 'guest'} />
        <Badge variant={event.is_public ? 'public' : 'private'} />
      </div>
    </div>

    <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
      <span className="flex items-center gap-1.5">
        <Calendar className="h-3.5 w-3.5 text-zinc-400" />
        {formatDate(event.date)}
      </span>
      <span className="flex items-center gap-1.5">
        <Clock className="h-3.5 w-3.5 text-zinc-400" />
        {formatTime(event.time)}
      </span>
      {event.location && (
        <span className="flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5 text-zinc-400" />
          {event.location}
        </span>
      )}
    </div>

    <div className="mt-3 flex items-center justify-between">
      <span className="flex items-center gap-1.5 text-xs text-zinc-500">
        <Users className="h-3.5 w-3.5" />
        {event.total_participants} participant{event.total_participants !== 1 ? 's' : ''} &middot; {event.attending_count} attending
      </span>
      <span className="text-xs text-zinc-400">by {event.owner_name}</span>
    </div>
  </Link>
);

export default EventCard;
