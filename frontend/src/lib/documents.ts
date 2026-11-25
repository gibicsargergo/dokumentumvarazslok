// Stub-backed client for the documents page.
// Drop-in replacement for the real backend API — the page only talks to this
// module, so swapping these functions for fetch calls later (or to WebSocket
// equivalents) should not require any page changes.
import { mockDocuments } from './documentsStub';
import type { Document, DocumentType, DocumentVisibility } from '../types/document';

export const ALLOWED_EXTENSIONS = [
  '.txt',
  '.md',
  '.pdf',
  '.jpg',
  '.jpeg',
  '.png',
  '.webp',
] as const;

const TEXT_EXTENSIONS = ['.txt', '.md'];
const PDF_EXTENSIONS = ['.pdf'];
const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];

export type UploadDraft = {
  filename: string;
  name: string;
  category: string;
  labels: string[];
  visibility: DocumentVisibility;
};

export type DocumentUpdate = Partial<
  Pick<Document, 'name' | 'category' | 'labels' | 'visibility'>
>;

export function extensionOf(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx === -1 ? '' : filename.slice(idx).toLowerCase();
}

export function isAllowedExtension(filename: string): boolean {
  return (ALLOWED_EXTENSIONS as readonly string[]).includes(extensionOf(filename));
}

export function typeForFilename(filename: string): DocumentType {
  const ext = extensionOf(filename);
  if (TEXT_EXTENSIONS.includes(ext)) return 'text';
  if (PDF_EXTENSIONS.includes(ext)) return 'pdf';
  if (IMAGE_EXTENSIONS.includes(ext)) return 'image';
  throw new Error(`Unsupported file type: '${filename}'`);
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

export function todayStamp(): string {
  return new Date().toISOString().slice(0, 10);
}

// -- stub-backed "API" (to be replaced by fetch calls) -------------------

export async function listDocuments(): Promise<Document[]> {
  return mockDocuments.map((doc) => ({ ...doc, labels: [...doc.labels] }));
}

export async function uploadDocument(
  draft: UploadDraft & { uploaderId: string; uploaderName: string },
): Promise<Document> {
  return {
    id: crypto.randomUUID(),
    name: draft.name.trim() || fileStem(draft.filename),
    type: typeForFilename(draft.filename),
    category: draft.category.trim(),
    uploadedAt: todayStamp(),
    uploaderId: draft.uploaderId,
    uploaderName: draft.uploaderName,
    labels: draft.labels,
    visibility: draft.visibility,
  };
}

export async function updateDocument(
  doc: Document,
  patch: DocumentUpdate,
): Promise<Document> {
  return { ...doc, ...patch };
}

export async function deleteDocument(_id: string): Promise<void> {
  // no-op — removal happens in the page's local state
}
