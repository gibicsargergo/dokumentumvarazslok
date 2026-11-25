// Documents come from the merged backend: GET /documents returns the vector
// index view (title/category/tags/chunks), not the filestore metadata.
export type DocumentVisibility = 'public' | 'private';

export interface Document {
  id: string;
  name: string;
  category: string;
  labels: string[];
  chunks: number;
}
