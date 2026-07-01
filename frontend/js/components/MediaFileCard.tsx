import { Download, FileText, Film, Image, Music, Trash2, ZoomIn } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import Button from './ui/Button';

import type { MediaFileItem } from '@/js/api';

interface MediaFileCardProps {
  file: MediaFileItem;
  canModify: boolean;
  onDelete: (fileUuid: string) => void;
  onDownload: (fileUuid: string) => void;
  onPreview?: (fileUuid: string) => void;
}

const FILE_TYPE_LABELS: Record<string, string> = {
  'image/jpeg': 'JPEG',
  'image/jpg': 'JPG',
  'image/png': 'PNG',
  'image/gif': 'GIF',
  'image/webp': 'WEBP',
  'application/pdf': 'PDF',
  'audio/mpeg': 'MP3',
  'video/mp4': 'MP4',
  'video/quicktime': 'MOV',
};

const FILE_TYPE_COLORS: Record<string, string> = {
  image: 'bg-emerald-100 text-emerald-700',
  video: 'bg-blue-100 text-blue-700',
  audio: 'bg-amber-100 text-amber-700',
  application: 'bg-zinc-100 text-zinc-700',
};

const getFileIcon = (fileType: string) => {
  if (fileType.startsWith('image/')) return <Image className="h-8 w-8" />;
  if (fileType.startsWith('video/')) return <Film className="h-8 w-8" />;
  if (fileType.startsWith('audio/')) return <Music className="h-8 w-8" />;
  return <FileText className="h-8 w-8" />;
};

const getTypeColor = (fileType: string): string => {
  const category = fileType.split('/')[0];
  return FILE_TYPE_COLORS[category] ?? FILE_TYPE_COLORS.application;
};

const MediaFileCard = ({ file, canModify, onDelete, onDownload, onPreview }: MediaFileCardProps) => {
  const [showConfirm, setShowConfirm] = useState(false);
  const [imgError, setImgError] = useState(false);

  // Reset error state when thumbnail_url changes (e.g. after delayed re-fetch)
  useEffect(() => {
    setImgError(false);
  }, [file.thumbnail_url]);
  const typeLabel = FILE_TYPE_LABELS[file.file_type] || file.file_type.split('/').pop()?.toUpperCase() || 'FILE';
  const isImage = file.file_type.startsWith('image/');
  const typeColor = getTypeColor(file.file_type);
  const hasThumbnail = isImage && file.thumbnail_url && !imgError;

  return (
    <div className="group rounded-xl border border-zinc-200 bg-white shadow-sm transition-all duration-200 hover:shadow-md overflow-hidden">
      <div
        className={`relative flex h-40 items-center justify-center ${hasThumbnail ? 'bg-zinc-100' : isImage ? 'bg-gradient-to-br from-emerald-50 to-emerald-100' : 'bg-gradient-to-br from-zinc-50 to-zinc-100'}`}
        onClick={() => hasThumbnail && onPreview?.(file.file_uuid)}
        role={hasThumbnail ? 'button' : undefined}
        tabIndex={hasThumbnail ? 0 : undefined}
      >
        {hasThumbnail ? (
          <>
            <img
              src={file.thumbnail_url!}
              alt={file.file_name}
              loading="lazy"
              className="h-full w-full object-cover"
              onError={() => setImgError(true)}
            />
            <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-all group-hover:bg-black/20 group-hover:opacity-100">
              <ZoomIn className="h-8 w-8 text-white drop-shadow-lg" />
            </div>
          </>
        ) : (
          <div className="text-zinc-400">
            {getFileIcon(file.file_type)}
          </div>
        )}
      </div>

      <div className="p-3">
        <p className="truncate text-sm font-medium text-slate-800" title={file.file_name}>
          {file.file_name}
        </p>

        <span className={`mt-1.5 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${typeColor}`}>
          {typeLabel}
        </span>

        <div className="mt-3 flex gap-1.5">
          <Button size="sm" variant="ghost" onClick={() => onDownload(file.file_uuid)} icon={<Download className="h-4 w-4" />}>
            Download
          </Button>
          {canModify && !showConfirm && (
            <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50 hover:text-red-700" onClick={() => setShowConfirm(true)} icon={<Trash2 className="h-4 w-4" />}>
              Delete
            </Button>
          )}
          {canModify && showConfirm && (
            <>
              <Button size="sm" variant="danger" onClick={() => onDelete(file.file_uuid)}>
                Confirm
              </Button>
              <Button size="sm" variant="secondary" onClick={() => setShowConfirm(false)}>
                Cancel
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediaFileCard;
