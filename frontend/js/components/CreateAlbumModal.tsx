import { FolderPlus, X } from 'lucide-react';
import React, { FormEvent, useState } from 'react';

import { Alert, Button, Checkbox, Input, Textarea } from './ui';

import { AlbumDetail, createAlbum } from '@/js/api';
import { extractBackendErrorMessage } from '@/js/utils';

interface CreateAlbumModalProps {
  eventUuid: string;
  onClose: () => void;
  onCreated: (album: AlbumDetail) => void;
}

const CreateAlbumModal = ({ eventUuid, onClose, onCreated }: CreateAlbumModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onSubmit = async (formEvent: FormEvent<HTMLFormElement>) => {
    formEvent.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      const response = await createAlbum(eventUuid, {
        name: name.trim(),
        description: description.trim() || undefined,
        is_public: isPublic,
      });
      onCreated(response.data);
      onClose();
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to create album.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-ink/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="animate-slide-up w-full max-w-lg rounded-2xl border border-border-subtle bg-surface-1 p-6 shadow-soft-lg"
        onClick={(clickEvent) => clickEvent.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <FolderPlus className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold text-ink">Create Album</h2>
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
            label="Album name"
            maxLength={255}
            required
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My awesome album"
          />

          <Textarea
            label="Description"
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this album about?"
          />

          <Checkbox
            label="Public album"
            description="Anyone with the link can view this album"
            checked={isPublic}
            onChange={(e) => setIsPublic(e.target.checked)}
          />

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoading}>
              Create Album
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateAlbumModal;
