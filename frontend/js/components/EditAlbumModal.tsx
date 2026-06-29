import { Pencil, X } from 'lucide-react';
import React, { FormEvent, useState } from 'react';

import { Alert, Button, Checkbox, Input, Textarea } from './ui';

import { AlbumDetail, updateAlbum } from '@/js/api';
import { extractBackendErrorMessage } from '@/js/utils';

interface EditAlbumModalProps {
  album: AlbumDetail;
  onClose: () => void;
  onUpdated: (album: AlbumDetail) => void;
}

const EditAlbumModal = ({ album, onClose, onUpdated }: EditAlbumModalProps) => {
  const [name, setName] = useState(album.name);
  const [description, setDescription] = useState(album.description || '');
  const [isPublic, setIsPublic] = useState(album.is_public);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const onSubmit = async (formEvent: FormEvent<HTMLFormElement>) => {
    formEvent.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      const response = await updateAlbum(album.album_uuid, {
        name: name.trim(),
        description: description.trim(),
        is_public: isPublic,
      });
      onUpdated(response.data);
      onClose();
    } catch (error) {
      setErrorMessage(extractBackendErrorMessage(error, 'Failed to update album.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="animate-fade-in fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div
        className="animate-slide-up w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl"
        onClick={(clickEvent) => clickEvent.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <Pencil className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Edit Album</h2>
          </div>
          <button className="rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-600" type="button" onClick={onClose}>
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
          />

          <Textarea
            label="Description"
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
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
              Save Changes
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditAlbumModal;
