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
    className="block rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition-all duration-200 hover:border-zinc-300 hover:shadow-md hover:scale-[1.01]"
    to={`/events/${eventUuid}/albums/${album.album_uuid}`}
  >
    <div className="flex items-start justify-between gap-2">
      <div className="flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-500">
          <FolderOpen className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-semibold text-slate-900">{album.name}</h2>
      </div>
      <Badge variant={album.is_public ? 'public' : 'private'} />
    </div>

    {album.description && (
      <p className="mt-2 line-clamp-2 text-sm text-slate-600">{album.description}</p>
    )}

    <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
      <span className="flex items-center gap-1.5">
        <Image className="h-3.5 w-3.5" />
        {album.mediafiles_count} file{album.mediafiles_count !== 1 ? 's' : ''}
      </span>
      <span>{album.event_name}</span>
    </div>
  </Link>
);

export default AlbumCard;
