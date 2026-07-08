import { ArrowLeft, CloudUpload, FolderOpen, HardDrive, Image, Pencil, Trash2 } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import {
  AlbumDetail as AlbumDetailType,
  deleteAlbum,
  deleteMediaFile,
  getAlbumDetail,
  getMediaFileDownloadUrl,
  listMediaFiles,
  MediaFileItem,
} from '@/js/api';
import EditAlbumModal from '@/js/components/EditAlbumModal';
import FileUploadZone from '@/js/components/FileUploadZone';
import MediaFileCard from '@/js/components/MediaFileCard';
import PhotoLightbox from '@/js/components/PhotoLightbox';
import { Alert, Badge, Button, Card, ConfirmDialog, EmptyState, LoadingSpinner, PageLayout, StatCard } from '@/js/components/ui';
import { useAuth } from '@/js/context/AuthContext';
import { extractBackendErrorMessage } from '@/js/utils';

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, index);
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const AlbumDetailPage = () => {
  const { eventUuid, albumUuid } = useParams<{ eventUuid: string; albumUuid: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [album, setAlbum] = useState<AlbumDetailType | null>(null);
  const [files, setFiles] = useState<MediaFileItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    if (!albumUuid || !eventUuid) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [albumResponse, filesResponse] = await Promise.allSettled([
        getAlbumDetail(albumUuid),
        listMediaFiles({ event_uuid: eventUuid }),
      ]);

      if (albumResponse.status === 'fulfilled') {
        setAlbum(albumResponse.value.data);
      } else {
        setErrorMessage(extractBackendErrorMessage(albumResponse.reason, 'Failed to load album.'));
      }

      if (filesResponse.status === 'fulfilled') {
        const allFiles = filesResponse.value.data.files || [];
        setFiles(allFiles.filter((file) => file.album_uuid === albumUuid));
      }
    } finally {
      setIsLoading(false);
    }
  }, [albumUuid, eventUuid]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const canModify = Boolean(user && album);

  const handleDelete = async () => {
    if (!albumUuid) return;
    setIsDeleting(true);

    try {
      await deleteAlbum(albumUuid);
      navigate(`/events/${eventUuid}/albums`);
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to delete album.'));
      setShowDeleteDialog(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDownload = async (fileUuid: string) => {
    try {
      const response = await getMediaFileDownloadUrl(fileUuid);
      window.open(response.data.download_url, '_blank');
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to get download URL.'));
    }
  };

  const handleDeleteFile = async (fileUuid: string) => {
    try {
      await deleteMediaFile(fileUuid);
      setFiles((prev) => prev.filter((file) => file.file_uuid !== fileUuid));
      setStatusMessage('File deleted.');
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to delete file.'));
    }
  };

  const handleAlbumUpdated = (updated: AlbumDetailType) => {
    setAlbum(updated);
    setStatusMessage('Album updated successfully.');
  };

  const imageFiles = files.filter((f) => f.file_type.startsWith('image/'));

  const handlePreview = (fileUuid: string) => {
    const index = imageFiles.findIndex((f) => f.file_uuid === fileUuid);
    if (index >= 0) setLightboxIndex(index);
  };

  return (
    <PageLayout>
      <Link
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
        to={`/events/${eventUuid}/albums`}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Albums
      </Link>

      {isLoading && <LoadingSpinner message="Loading album..." />}

      {!isLoading && errorMessage && !album && (
        <Alert variant="error">{errorMessage}</Alert>
      )}

      {!isLoading && album && (
        <>
          {/* Header */}
          <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                  <FolderOpen className="h-5 w-5" />
                </div>
                <h1 className="text-3xl font-bold tracking-tight text-ink">{album.name}</h1>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant={album.is_public ? 'public' : 'private'} />
              </div>
            </div>
            <div className="flex gap-2">
              {canModify && (
                <Button variant="secondary" onClick={() => setShowEditModal(true)} icon={<Pencil className="h-4 w-4" />}>
                  Edit
                </Button>
              )}
              {canModify && (
                <Button variant="danger" onClick={() => setShowDeleteDialog(true)} icon={<Trash2 className="h-4 w-4" />}>
                  Delete
                </Button>
              )}
            </div>
          </div>

          {/* Alerts */}
          {errorMessage && (
            <div className="mb-4">
              <Alert variant="error" onDismiss={() => setErrorMessage(null)}>{errorMessage}</Alert>
            </div>
          )}
          {statusMessage && (
            <div className="mb-4">
              <Alert variant="success" onDismiss={() => setStatusMessage(null)}>{statusMessage}</Alert>
            </div>
          )}

          {album.description && (
            <p className="mb-4 text-sm leading-relaxed text-ink-muted whitespace-pre-wrap">{album.description}</p>
          )}

          {/* Stats */}
          <div className="mb-6 grid grid-cols-2 gap-3">
            <StatCard label="Files" value={album.file_count} icon={<Image className="h-5 w-5" />} />
            <StatCard label="Total Size" value={formatFileSize(album.total_file_size)} icon={<HardDrive className="h-5 w-5" />} />
          </div>

          {/* Upload Zone */}
          <Card padding="lg">
            <div className="mb-3 flex items-center gap-2">
              <CloudUpload className="h-5 w-5 text-brand-500" />
              <h3 className="text-lg font-semibold text-ink">Upload Files</h3>
            </div>
            {user && (
              <FileUploadZone
                eventUuid={eventUuid!}
                albumUuid={albumUuid!}
                userId={user.id}
                onUploadComplete={() => {
                  loadData();
                  // Delayed re-fetch so thumbnails generated by Celery are available
                  setTimeout(() => loadData(), 3000);
                }}
              />
            )}
          </Card>

          {/* Files Grid */}
          <div className="mt-6">
            <div className="mb-4 flex items-center gap-2">
              <Image className="h-5 w-5 text-brand-500" />
              <h3 className="text-lg font-semibold text-ink">Files</h3>
              {files.length > 0 && <span className="text-sm text-ink-faint">({files.length})</span>}
            </div>
            {files.length === 0 ? (
              <EmptyState
                title="No files yet"
                message="Upload files to this album using the upload zone above."
                icon={<Image className="h-12 w-12" />}
              />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {files.map((file) => (
                  <MediaFileCard
                    key={file.file_uuid}
                    file={file}
                    canModify={canModify}
                    onDelete={handleDeleteFile}
                    onDownload={handleDownload}
                    onPreview={handlePreview}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Modals */}
          {showEditModal && (
            <EditAlbumModal
              album={album}
              onClose={() => setShowEditModal(false)}
              onUpdated={handleAlbumUpdated}
            />
          )}
          {showDeleteDialog && (
            <ConfirmDialog
              title="Delete Album"
              message={`Are you sure you want to delete "${album.name}"? This action cannot be undone.`}
              confirmLabel="Delete"
              variant="danger"
              isLoading={isDeleting}
              onConfirm={handleDelete}
              onCancel={() => setShowDeleteDialog(false)}
            />
          )}
          {lightboxIndex !== null && imageFiles.length > 0 && (
            <PhotoLightbox
              files={imageFiles}
              currentIndex={lightboxIndex}
              onClose={() => setLightboxIndex(null)}
              onNavigate={setLightboxIndex}
            />
          )}
        </>
      )}
    </PageLayout>
  );
};

export default AlbumDetailPage;
