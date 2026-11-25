import { useEffect, useState } from 'react';
import type { Document } from '../types/document';
import {
  deleteDocument,
  listDocuments,
  updateDocument,
  uploadDocument,
  type DocumentUpdate,
  type UploadDraft,
} from '../lib/documents';
import UploadDocumentModal from '../components/UploadDocumentModal';
import EditDocumentModal from '../components/EditDocumentModal';

// Temporary user until authentication is implemented
const CURRENT_USER = { id: 'user1', name: 'Alice', isAdmin: false };

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

  const visibleDocuments = documents.filter(
    (doc) => doc.visibility === 'public' || doc.uploaderId === CURRENT_USER.id,
  );

  function canEdit(doc: Document) {
    return doc.uploaderId === CURRENT_USER.id || CURRENT_USER.isAdmin;
  }

  async function handleUpload(draft: UploadDraft) {
    const doc = await uploadDocument({
      ...draft,
      uploaderId: CURRENT_USER.id,
      uploaderName: CURRENT_USER.name,
    });
    setDocuments((docs) => [...docs, doc]);
    setUploadOpen(false);
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
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold">Documents</h1>
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white transition hover:bg-emphasis"
        >
          Add document
        </button>
      </div>

      {loadError && (
        <p role="alert" className="mb-4 text-sm text-red-600">
          {loadError}
        </p>
      )}

      {visibleDocuments.length === 0 ? (
        <p className="text-muted">No documents yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="w-full text-left">
            <thead className="bg-track">
              <tr>
                <th className="p-4">Name</th>
                <th className="p-4">Type</th>
                <th className="p-4">Category</th>
                <th className="p-4">Uploaded</th>
                <th className="p-4">Uploader</th>
                <th className="p-4">Labels</th>
                <th className="p-4">Visibility</th>
                <th className="p-4">Actions</th>
              </tr>
            </thead>

            <tbody>
              {visibleDocuments.map((doc) => {
                const isOwner = doc.uploaderId === CURRENT_USER.id;

                return (
                  <tr key={doc.id} className="border-t border-line">
                    <td className="p-4">{doc.name}</td>
                    <td className="p-4">{doc.type}</td>
                    <td className="p-4">{doc.category}</td>
                    <td className="p-4">{doc.uploadedAt}</td>
                    <td className="p-4">{isOwner ? doc.uploaderName : '—'}</td>
                    <td className="p-4">{doc.labels.join(', ')}</td>
                    <td className="p-4">{doc.visibility}</td>
                    <td className="p-4">
                      {canEdit(doc) && (
                        <button
                          type="button"
                          onClick={() => setEditing(doc)}
                          className="text-subtle transition hover:text-ink"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
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

      {editing !== null && (
        <EditDocumentModal
          document={editing}
          onClose={() => setEditing(null)}
          onSave={handleSave}
          onDelete={handleDelete}
        />
      )}
    </main>
  );
}
