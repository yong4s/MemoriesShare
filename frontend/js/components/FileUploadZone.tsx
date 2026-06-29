import axios from 'axios';
import { AlertCircle, CheckCircle, CloudUpload, Loader2 } from 'lucide-react';
import React, { useCallback, useRef, useState } from 'react';

import Button from './ui/Button';

import { confirmMediaUpload, requestMediaUploadUrl } from '@/js/api';

interface FileUploadZoneProps {
  eventUuid: string;
  albumUuid: string;
  userId: number;
  onUploadComplete: () => void;
}

interface UploadItem {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'confirming' | 'done' | 'error';
  error?: string;
}

const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/gif',
  'application/pdf',
  'audio/mpeg',
  'video/mp4',
  'video/quicktime',
];

const ACCEPT_STRING = '.jpg,.jpeg,.png,.gif,.pdf,.mp3,.mp4,.mov';

let uploadIdCounter = 0;

const FileUploadZone = ({ eventUuid, albumUuid, userId, onUploadComplete }: FileUploadZoneProps) => {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const updateUpload = useCallback((id: string, patch: Partial<UploadItem>) => {
    setUploads((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const uploadFile = useCallback(
    async (item: UploadItem) => {
      try {
        updateUpload(item.id, { status: 'uploading', progress: 0 });

        const presignedResponse = await requestMediaUploadUrl({
          event_uuid: eventUuid,
          album_uuid: albumUuid,
          file_name: item.file.name,
          content_type: item.file.type || 'application/octet-stream',
        });

        const { url, fields, s3_key, file_uuid } = presignedResponse.data;

        const formData = new FormData();
        Object.entries(fields).forEach(([key, value]) => {
          formData.append(key, value);
        });
        // S3 requires the file field to be appended last.
        formData.append('file', item.file);

        await axios.post(url, formData, {
          onUploadProgress: (progressEvent) => {
            const percent = progressEvent.total ? Math.round((progressEvent.loaded / progressEvent.total) * 100) : 0;
            updateUpload(item.id, { progress: percent });
          },
        });

        updateUpload(item.id, { status: 'confirming', progress: 100 });

        await confirmMediaUpload({
          event_uuid: eventUuid,
          album_uuid: albumUuid,
          s3_key,
          file_type: item.file.type || 'application/octet-stream',
          file_name: item.file.name,
          user_id: userId,
          file_uuid,
        });

        updateUpload(item.id, { status: 'done' });
        onUploadComplete();
      } catch (error) {
        const message = axios.isAxiosError(error) ? error.response?.data?.error || error.message : 'Upload failed';
        updateUpload(item.id, { status: 'error', error: message });
      }
    },
    [eventUuid, albumUuid, userId, updateUpload, onUploadComplete],
  );

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      const newItems: UploadItem[] = Array.from(files)
        .filter((file) => ACCEPTED_TYPES.includes(file.type))
        .map((file) => ({
          id: `upload-${++uploadIdCounter}`,
          file,
          progress: 0,
          status: 'pending' as const,
        }));

      setUploads((prev) => [...prev, ...newItems]);
      newItems.forEach((item) => uploadFile(item));
    },
    [uploadFile],
  );

  const handleDrop = useCallback(
    (dropEvent: React.DragEvent) => {
      dropEvent.preventDefault();
      setIsDragOver(false);
      handleFiles(dropEvent.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleInputChange = useCallback(
    (inputEvent: React.ChangeEvent<HTMLInputElement>) => {
      if (inputEvent.target.files) {
        handleFiles(inputEvent.target.files);
        inputEvent.target.value = '';
      }
    },
    [handleFiles],
  );

  const clearCompleted = () => {
    setUploads((prev) => prev.filter((item) => item.status !== 'done' && item.status !== 'error'));
  };

  const hasFinished = uploads.some((item) => item.status === 'done' || item.status === 'error');

  const statusIcon = (item: UploadItem) => {
    if (item.status === 'done') return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    if (item.status === 'error') return <AlertCircle className="h-4 w-4 text-red-500" />;
    if (item.status === 'uploading' || item.status === 'confirming') return <Loader2 className="h-4 w-4 animate-spin text-brand-500" />;
    return null;
  };

  return (
    <div className="space-y-3">
      <div
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all duration-200 ${isDragOver ? 'border-brand-500 bg-brand-50' : 'border-zinc-300 hover:border-zinc-400'}`}
        onDragOver={(dragEvent) => {
          dragEvent.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
      >
        <CloudUpload className={`mb-3 h-10 w-10 ${isDragOver ? 'text-brand-500' : 'text-zinc-400'}`} />
        <p className="mb-2 text-sm text-zinc-600">Drag and drop files here, or</p>
        <Button size="sm" variant="secondary" onClick={() => inputRef.current?.click()}>
          Browse Files
        </Button>
        <p className="mt-2 text-xs text-zinc-400">JPG, PNG, GIF, PDF, MP3, MP4, MOV</p>
        <input ref={inputRef} className="hidden" type="file" multiple accept={ACCEPT_STRING} onChange={handleInputChange} />
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((item) => (
            <div key={item.id} className="rounded-lg border border-zinc-200 bg-white px-3 py-2.5">
              <div className="flex items-center justify-between text-sm">
                <span className="truncate text-slate-800">{item.file.name}</span>
                <span className="ml-2 flex shrink-0 items-center gap-1.5 text-xs font-medium">
                  {statusIcon(item)}
                  <span className={item.status === 'done' ? 'text-emerald-600' : item.status === 'error' ? 'text-red-600' : 'text-zinc-500'}>
                    {item.status === 'uploading' ? `${item.progress}%` : item.status === 'confirming' ? 'Confirming...' : item.status === 'done' ? 'Done' : item.status === 'error' ? 'Failed' : 'Pending'}
                  </span>
                </span>
              </div>
              {(item.status === 'uploading' || item.status === 'confirming') && (
                <div className="mt-1.5 h-1.5 rounded-full bg-zinc-100">
                  <div className="h-1.5 rounded-full bg-brand-600 transition-all duration-300" style={{ width: `${item.progress}%` }} />
                </div>
              )}
              {item.status === 'error' && item.error && (
                <p className="mt-1 text-xs text-red-500">{item.error}</p>
              )}
            </div>
          ))}
          {hasFinished && (
            <button className="text-xs text-zinc-500 hover:text-zinc-700 transition-colors" type="button" onClick={clearCompleted}>
              Clear completed
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default FileUploadZone;
