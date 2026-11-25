import { useState } from 'react';
import Modal from './Modal';
import { splitLabels, type DocumentUpdate } from '../lib/documents';
import type { Document } from '../types/document';

type Props = {
  document: Document;
  onClose: () => void;
  onSave: (id: string, patch: DocumentUpdate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
};

export default function EditDocumentModal({ document, onClose, onSave, onDelete }: Props) {
  const [name, setName] = useState(document.name);
  const [category, setCategory] = useState(document.category);
  const [labelsInput, setLabelsInput] = useState(document.labels.join(', '));
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!name.trim() || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(document.id, {
        name: name.trim(),
        category: category.trim(),
        labels: splitLabels(labelsInput),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (deleting) return;
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
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <Modal
      title="Edit document"
      onClose={onClose}
      footer={
        <>
          {confirming ? (
            <>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded-lg border border-line px-4 py-2 text-sm text-subtle transition hover:text-emphasis"
              >
                Stop
              </button>
              <button
                type="button"
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Confirm delete'}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setConfirming(true)}
                className="mr-auto rounded-lg border border-red-200 px-4 py-2 text-sm text-red-600 transition hover:bg-red-50"
              >
                Delete
              </button>
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
          )}
        </>
      }
    >
      <label className="block text-sm font-medium text-emphasis">
        Name
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
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

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {error}
        </p>
      )}
    </Modal>
  );
}
