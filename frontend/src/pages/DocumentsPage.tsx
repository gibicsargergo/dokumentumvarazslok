import { useEffect, useState } from 'react';
import type { Document } from '../types/document';
import {
  deleteDocument,
  downloadUrl,
  listDocuments,
  updateDocument,
  uploadDocument,
  type DocumentUpdate,
  type UploadDraft,
} from '../lib/documents';
import UploadDocumentModal from '../components/UploadDocumentModal';
import EditDocumentModal from '../components/EditDocumentModal';

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editing, setEditing] = useState<Document | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listDocuments()
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : 'Failed to load documents');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function refresh() {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load documents');
    }
  }

  async function handleUpload(draft: UploadDraft) {
    await uploadDocument(draft);
    setUploadOpen(false);
    await refresh();
  }

  async function handleSave(id: string, patch: DocumentUpdate) {
    const doc = documents.find((d) => d.id === id);
    if (!doc) return;
    const updated = await updateDocument(doc, patch);
    setDocuments((docs) => docs.map((d) => (d.id === id ? updated : d)));
    setEditing(null);
  }

  async function handleDelete(id: string) {
    await deleteDocument(id);
    setDocuments((docs) => docs.filter((d) => d.id !== id));
    setEditing(null);
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink">Documents</h1>
          <p className="mt-1 text-sm text-muted">
            {documents.length} document{documents.length === 1 ? '' : 's'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition hover:bg-emphasis"
        >
          Add document
        </button>
      </header>

      {loadError && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load documents: {loadError}
        </p>
      )}

      {documents.length === 0 && !loadError ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-20 text-center">
          <p className="text-lg font-medium text-ink">No documents yet</p>
          <p className="max-w-sm text-sm text-muted">
            Upload your first document to get started.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase tracking-wide text-subtle">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Labels</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3 font-medium">Uploader</th>
                <th className="px-4 py-3 font-medium">Chunks</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-line last:border-0">
                  <td className="max-w-[280px] truncate px-4 py-3 font-medium text-ink">
                    {doc.name}
                  </td>
                  <td className="px-4 py-3 text-body">{doc.category || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {doc.labels.length === 0 ? (
                        <span className="text-subtle">—</span>
                      ) : (
                        doc.labels.map((label) => (
                          <span
                            key={label}
                            className="rounded-full bg-track px-2 py-0.5 text-xs text-subtle"
                          >
                            {label}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-body">
                    {formatDate(doc.uploadedAt)}
                  </td>
                  <td className="max-w-[200px] truncate px-4 py-3 text-body">
                    {doc.uploaderEmail ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-body">{doc.chunks}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    <a
                      href={downloadUrl(doc.id)}
                      download={doc.filename}
                      className="mr-2 inline-block rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-subtle transition hover:text-emphasis"
                    >
                      Download
                    </a>
                    <button
                      type="button"
                      onClick={() => setEditing(doc)}
                      className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-subtle transition hover:text-emphasis"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {uploadOpen && (
        <UploadDocumentModal
          onClose={() => setUploadOpen(false)}
          onUpload={handleUpload}
        />
      )}
      {editing && (
        <EditDocumentModal
          document={editing}
          onClose={() => setEditing(null)}
          onSave={handleSave}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
