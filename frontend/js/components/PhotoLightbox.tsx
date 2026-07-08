import { ChevronLeft, ChevronRight, Download, X } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';

import { getMediaFileDownloadUrl } from '@/js/api';

import type { MediaFileItem } from '@/js/api';

interface PhotoLightboxProps {
  files: MediaFileItem[];
  currentIndex: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

const PhotoLightbox = ({ files, currentIndex, onClose, onNavigate }: PhotoLightboxProps) => {
  const [fullUrl, setFullUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const file = files[currentIndex];
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < files.length - 1;

  const loadFullImage = useCallback(async (fileUuid: string) => {
    setIsLoading(true);
    setFullUrl(null);
    try {
      const response = await getMediaFileDownloadUrl(fileUuid);
      setFullUrl(response.data.download_url);
    } catch {
      setFullUrl(file?.thumbnail_url ?? null);
    } finally {
      setIsLoading(false);
    }
  }, [file?.thumbnail_url]);

  useEffect(() => {
    if (file) {
      loadFullImage(file.file_uuid);
    }
  }, [file, loadFullImage]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft' && hasPrev) onNavigate(currentIndex - 1);
      if (e.key === 'ArrowRight' && hasNext) onNavigate(currentIndex + 1);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onNavigate, currentIndex, hasPrev, hasNext]);

  // Prevent body scroll while lightbox is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  const handleDownload = () => {
    if (fullUrl) {
      window.open(fullUrl, '_blank');
    }
  };

  if (!file) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      onClick={onClose}
    >
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <p className="truncate text-sm font-medium text-white/80 max-w-[60%]">{file.file_name}</p>
        <div className="flex items-center gap-2">
          <span className="text-sm text-white/60">
            {currentIndex + 1} / {files.length}
          </span>
          <button
            type="button"
            aria-label="Download original"
            className="rounded-lg p-2 text-white/80 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
            onClick={handleDownload}
            title="Download original"
          >
            <Download className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Close"
            className="rounded-lg p-2 text-white/80 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
            onClick={onClose}
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Navigation arrows */}
      {hasPrev && (
        <button
          type="button"
          aria-label="Previous photo"
          className="absolute left-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/80 transition-colors hover:bg-black/60 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
          onClick={(e) => { e.stopPropagation(); onNavigate(currentIndex - 1); }}
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}
      {hasNext && (
        <button
          type="button"
          aria-label="Next photo"
          className="absolute right-2 top-1/2 z-10 -translate-y-1/2 rounded-full bg-black/40 p-2 text-white/80 transition-colors hover:bg-black/60 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
          onClick={(e) => { e.stopPropagation(); onNavigate(currentIndex + 1); }}
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}

      {/* Image */}
      <div className="flex max-h-[85vh] max-w-[90vw] items-center justify-center" onClick={(e) => e.stopPropagation()}>
        {isLoading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-white/20 border-t-white/80" />
            {file.thumbnail_url && (
              <img
                src={file.thumbnail_url}
                alt={file.file_name}
                className="max-h-[70vh] max-w-[80vw] rounded-lg object-contain opacity-40"
              />
            )}
          </div>
        ) : fullUrl ? (
          <img
            src={fullUrl}
            alt={file.file_name}
            className="max-h-[85vh] max-w-[90vw] rounded-lg object-contain"
          />
        ) : (
          <p className="text-white/60">Failed to load image</p>
        )}
      </div>
    </div>
  );
};

export default PhotoLightbox;
