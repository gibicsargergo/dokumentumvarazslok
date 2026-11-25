// Backend client for the documents page (see backend/api.py).
// Requests go to /api, which the Vite dev server proxies to the FastAPI backend.
import type { Document, DocumentVisibility } from '../types/document';

export const ALLOWED_EXTENSIONS = [
  '.txt',
  '.md',
  '.pdf',
  '.jpg',
  '.jpeg',
  '.png',
  '.webp',
] as const;

export type UploadDraft = {
  file: File;
  name: string;
  category: string;
  labels: string[];
  visibility: DocumentVisibility;
};

export type DocumentUpdate = Partial<
  Pick<Document, 'name' | 'category' | 'labels'>
>;

// -- helpers (also used by the upload modal) ────────────────────────────────

export function extensionOf(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx === -1 ? '' : filename.slice(idx).toLowerCase();
}

export function isAllowedExtension(filename: string): boolean {
  return (ALLOWED_EXTENSIONS as readonly string[]).includes(extensionOf(filename));
}

export function fileStem(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx === -1 ? filename : filename.slice(0, idx);
}

export function splitLabels(input: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of input.split(',')) {
    const label = raw.trim();
    if (label && !seen.has(label)) {
      seen.add(label);
      out.push(label);
    }
  }
  return out;
}

// -- response mapping ────────────────────────────────────────────────────────

// Shape of the merged backend's GET /documents (kb.list_documents).
type KbDocument = {
  id: string;
  title: string;
  category: string;
  tags: string[];
  chunks: number;
  source: string;
};

function mapKbDocument(doc: Partial<KbDocument>): Document {
  return {
    id: doc.id ?? '',
    name: doc.title ?? '',
    category: doc.category ?? '',
    labels: doc.tags ?? [],
    chunks: doc.chunks ?? 0,
  };
}

type AddResponse = {
  status: string;
  indexed: boolean;
  chunks_created: number;
  file: {
    id: string;
    index_id: string | null;
  };
  error?: string;
};

type UpdateResponse = {
  status: string;
  file_id: string;
  // Backend resolves `stored.index_id or stored.id`, so this is always set.
  index_id: string;
  updated_chunks: number;
};

// -- HTTP helpers ────────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { credentials: 'include', ...init });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

// -- API ─────────────────────────────────────────────────────────────────────

export async function listDocuments(): Promise<Document[]> {
  const docs = await request<KbDocument[]>('/documents');
  return docs.map(mapKbDocument);
}

export async function uploadDocument(draft: UploadDraft): Promise<void> {
  const form = new FormData();
  form.append('file', draft.file);
  form.append('title', draft.name);
  form.append('category', draft.category);
  form.append('tags', draft.labels.join(', '));
  form.append('is_private', draft.visibility === 'private' ? 'true' : 'false');

  await request<AddResponse>('/add', {
    method: 'POST',
    body: form,
  });
  // The new document lives in the index; the caller refetches the list.
}

// PATCH mirrors the flow branch's shape: title/category/tags/is_private.
// The response carries only the index-side result ({ status, doc_id,
// updated_chunks }), so the row is updated locally.
export async function updateDocument(
  doc: Document,
  patch: DocumentUpdate,
): Promise<Document> {
  const body: Record<string, unknown> = {};
  if (patch.name !== undefined && patch.name.trim()) body.title = patch.name.trim();
  if (patch.category !== undefined) body.category = patch.category.trim();
  if (patch.labels !== undefined) body.tags = patch.labels;

  await request<UpdateResponse>(`/documents/${encodeURIComponent(doc.id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return { ...doc, ...patch };
}

export async function deleteDocument(id: string): Promise<void> {
  await request<{ status: string; file_id: string; index_id: string; deleted_chunks: number }>('/delete', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: id }),
  });
}
