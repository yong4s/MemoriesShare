import { ArrowLeft, FolderOpen, FolderPlus } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { AlbumListItem, listEventAlbums } from '@/js/api';
import AlbumCard from '@/js/components/AlbumCard';
import CreateAlbumModal from '@/js/components/CreateAlbumModal';
import { Alert, EmptyState, LoadingSpinner, PageHeader, PageLayout } from '@/js/components/ui';
import { extractBackendErrorMessage } from '@/js/utils';

const AlbumList = () => {
  const { eventUuid } = useParams<{ eventUuid: string }>();

  const [albums, setAlbums] = useState<AlbumListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const loadAlbums = useCallback(async () => {
    if (!eventUuid) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await listEventAlbums(eventUuid);
      setAlbums(response.data);
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to load albums.'));
    } finally {
      setIsLoading(false);
    }
  }, [eventUuid]);

  useEffect(() => {
    loadAlbums();
  }, [loadAlbums]);

  return (
    <PageLayout>
      <Link
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
        to={`/events/${eventUuid}`}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Event
      </Link>

      <PageHeader
        title="Albums"
        action={{ label: 'Create Album', onClick: () => setShowCreateModal(true), icon: <FolderPlus className="h-4 w-4" /> }}
      />

      {errorMessage && (
        <div className="mb-4">
          <Alert variant="error" onDismiss={() => setErrorMessage(null)}>{errorMessage}</Alert>
        </div>
      )}

      {isLoading && <LoadingSpinner message="Loading albums..." />}

      {!isLoading && !errorMessage && albums.length === 0 && (
        <EmptyState
          title="No albums yet"
          message="Create an album to start organizing your media files."
          action={{ label: 'Create Album', onClick: () => setShowCreateModal(true) }}
          icon={<FolderOpen className="h-12 w-12" />}
        />
      )}

      {!isLoading && albums.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {albums.map((album) => (
            <AlbumCard key={album.album_uuid} album={album} eventUuid={eventUuid!} />
          ))}
        </div>
      )}

      {showCreateModal && eventUuid && (
        <CreateAlbumModal
          eventUuid={eventUuid}
          onClose={() => setShowCreateModal(false)}
          onCreated={() => loadAlbums()}
        />
      )}
    </PageLayout>
  );
};

export default AlbumList;
