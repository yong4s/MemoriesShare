import { FolderOpen, Image } from 'lucide-react';
import React from 'react';
import { Link } from 'react-router';

import Badge from './ui/Badge';

import type { AlbumListItem } from '@/js/api';

interface AlbumCardProps {
  album: AlbumListItem;
  eventUuid: string;
}

const AlbumCard = ({ album, eventUuid }: AlbumCardProps) => (
  <Link
    className="group block rounded-2xl px-5 py-4.5 transition-colors duration-200 hover:bg-surface-1"
    to={`/events/${eventUuid}/albums/${album.album_uuid}`}
  >
    <div className="flex items-start justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2.5">
        <FolderOpen className="h-4.5 w-4.5 shrink-0 text-ink-faint transition-colors duration-200 group-hover:text-brand-500" />
        <h2 className="truncate text-xl font-semibold leading-snug tracking-tight text-ink decoration-brand-400/40 decoration-2 underline-offset-4 group-hover:underline">
          {album.name}
        </h2>
      </div>
      <Badge variant={album.is_public ? 'public' : 'private'} />
    </div>

    {album.description && (
      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-muted">{album.description}</p>
    )}

    <div className="mt-3 h-px bg-border-subtle" />

    <div className="mt-3 flex items-center justify-between text-xs text-ink-faint">
      <span className="flex items-center gap-1.5">
        <Image className="h-3.5 w-3.5" />
        <span className="font-medium text-ink-muted">{album.mediafiles_count}</span>
        {album.mediafiles_count !== 1 ? ' files' : ' file'}
      </span>
      <span>{album.event_name}</span>
    </div>
  </Link>
);

export default AlbumCard;
