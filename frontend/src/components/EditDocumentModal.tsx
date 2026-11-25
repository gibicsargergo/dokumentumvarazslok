import { useState } from 'react';
import Modal from './Modal';
import ToggleSwitch, { type Option } from './ToggleSwitch';
import { splitLabels, type DocumentUpdate } from '../lib/documents';
import type { Document, DocumentVisibility } from '../types/document';

const VISIBILITY_OPTIONS: Option[] = [
  { value: 'public', label: 'Public' },
  { value: 'private', label: 'Private' },
];

const INPUT_CLASS =
  'mt-1 w-full rounded-lg border border-line px-3 py-2 text-sm font-normal text-ink outline-none transition focus:border-transparent focus:shadow-[0_1px_6px_rgba(0,0,0,0.2)]';

type Props = {
  document: Document;
  onClose: () => void;
  onSave: (id: string, patch: DocumentUpdate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
};

export default function EditDocumentModal({
  document,
  onClose,
  onSave,
  onDelete,
}: Props) {
  const [name, setName] = useState(document.name);
  const [category, setCategory] = useState(document.category);
  const [labelsInput, setLabelsInput] = useState(document.labels.join(', '));
  const [visibility, setVisibility] = useState<DocumentVisibility>(
    document.visibility,
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleSave() {
    if (!name.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(document.id, {
        name: name.trim(),
        category: category.trim(),
        labels: splitLabels(labelsInput),
        visibility,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await onDelete(document.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
      setConfirming(false);
      setDeleting(false);
    }
  }

  return (
    <Modal
      title="Edit document"
      onClose={onClose}
      footer={
        <>
          {confirming ? (
            <span className="mr-auto flex items-center gap-2">
              <button
                type="button"
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Confirm delete'}
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                disabled={deleting}
                className="rounded-lg border border-line px-3 py-2 text-sm text-subtle transition hover:text-emphasis"
              >
                Cancel
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="mr-auto rounded-lg px-3 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50"
            >
              Delete
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-line px-4 py-2 text-sm text-subtle transition hover:text-emphasis"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={!name.trim() || saving}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition hover:bg-emphasis disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </>
      }
    >
      {error && (
        <p role="alert" className="mb-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <label className="block text-sm font-medium text-emphasis">
        Name
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={INPUT_CLASS}
        />
      </label>

      <label className="mt-3 block text-sm font-medium text-emphasis">
        Category
        <input
          type="text"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className={INPUT_CLASS}
        />
      </label>

      <label className="mt-3 block text-sm font-medium text-emphasis">
        Labels{' '}
        <span className="font-normal text-subtle">(comma-separated)</span>
        <input
          type="text"
          value={labelsInput}
          onChange={(e) => setLabelsInput(e.target.value)}
          className={INPUT_CLASS}
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
