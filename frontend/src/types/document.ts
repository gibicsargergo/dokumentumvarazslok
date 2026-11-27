// Documents come from GET /documents, which lists the FileStore entries
// (upload date, uploader) joined with their chunk count from the vector index.
export type DocumentVisibility = 'public' | 'private';

export interface Document {
  id: string;
  name: string;
  category: string;
  labels: string[];
  chunks: number;
  filename: string;
  uploadedAt: string;
  uploaderId: string;
  uploaderEmail: string | null;
  visibility: DocumentVisibility;
}
