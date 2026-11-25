import { useRef, useState, type DragEvent } from 'react';
import Modal from './Modal';
import ToggleSwitch, { type Option } from './ToggleSwitch';
import {
  ALLOWED_EXTENSIONS,
  fileStem,
  isAllowedExtension,
  splitLabels,
  type UploadDraft,
} from '../lib/documents';
import type { DocumentVisibility } from '../types/document';

const VISIBILITY_OPTIONS: Option[] = [
  { value: 'public', label: 'Public' },
  { value: 'private', label: 'Private' },
];

const ACCEPT = ALLOWED_EXTENSIONS.join(',');

type Props = {
  onClose: () => void;
  onUpload: (draft: UploadDraft) => Promise<void>;
};

export default function UploadDocumentModal({ onClose, onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [labelsInput, setLabelsInput] = useState('');
  const [visibility, setVisibility] = useState<DocumentVisibility>('public');
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  function handleFile(f: File | undefined | null) {
    if (!f) return;
    if (!isAllowedExtension(f.name)) {
      setFile(null);
      setName('');
      setError(
        `Unsupported file type '${f.name}'. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
      );
      return;
    }
    setError(null);
    setFile(f);
    setName(fileStem(f.name));
  }

  function onDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(true);
  }

  function onDragEnter(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
  }

  function onDragLeave(event: DragEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setDragging(false);
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files?.[0]);
  }

  function onZoneKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      inputRef.current?.click();
    }
  }

  async function handleUpload() {
    if (!file || !name.trim() || uploading) return;
    setUploading(true);
    setError(null);
    try {
      await onUpload({
        file,
        name: name.trim(),
        category: category.trim(),
        labels: splitLabels(labelsInput),
        visibility,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  }

  return (
    <Modal
      title="Add document"
      onClose={onClose}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-line px-4 py-2 text-sm text-subtle transition hover:text-emphasis"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleUpload()}
            disabled={!file || !name.trim() || uploading}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition hover:bg-emphasis disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </>
      }
    >
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={onZoneKeyDown}
        onDragOver={onDragOver}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-8 text-center transition ${
          dragging
            ? 'border-ink bg-track'
            : 'border-line bg-track/40 hover:border-subtle'
        }`}
      >
        <p className="font-medium text-ink">Drag &amp; drop a file here</p>
        <p className="text-sm text-subtle">
          or click to browse — .txt, .md, .pdf, .jpg, .jpeg, .png, .webp
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            handleFile(e.target.files?.[0]);
            e.target.value = '';
          }}
        />
      </div>

      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {error}
        </p>
      )}

      {file && (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{file.name}</p>
            <p className="text-xs text-subtle">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setFile(null);
              setName('');
              setError(null);
            }}
            aria-label="Remove file"
            className="px-1 text-xl leading-none text-subtle transition hover:text-emphasis"
          >
            ×
          </button>
        </div>
      )}

      <label className="mt-4 block text-sm font-medium text-emphasis">
        Name
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Document name"
          className="mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm font-normal text-ink outline-none transition focus:border-transparent focus:shadow-[0_1px_6px_rgba(0,0,0,0.2)]"
        />
      </label>

      <label className="mt-3 block text-sm font-medium text-emphasis">
        Category
        <input
          type="text"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          placeholder="e.g. Development"
          className="mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm font-normal text-ink outline-none transition focus:border-transparent focus:shadow-[0_1px_6px_rgba(0,0,0,0.2)]"
        />
      </label>

      <label className="mt-3 block text-sm font-medium text-emphasis">
        Labels <span className="font-normal text-subtle">(comma-separated)</span>
        <input
          type="text"
          value={labelsInput}
          onChange={(e) => setLabelsInput(e.target.value)}
          placeholder="e.g. notes, meeting"
          className="mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm font-normal text-ink outline-none transition focus:border-transparent focus:shadow-[0_1px_6px_rgba(0,0,0,0.2)]"
        />
      </label>

      <div className="mt-4">
        <p className="text-sm font-medium text-emphasis">Visibility</p>
        <div className="mt-1">
          <ToggleSwitch
            value={visibility}
            options={VISIBILITY_OPTIONS}
            onChange={(v) => setVisibility(v as DocumentVisibility)}
          />
        </div>
      </div>
    </Modal>
  );
}
