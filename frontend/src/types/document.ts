export type DocumentType = 'text' | 'pdf' | 'image'

export type DocumentVisibility = 'public' | 'private'

export interface Document {
    id: string;
    name: string;
    type: DocumentType;
    category: string;
    uploadedAt: string;
    uploaderId: string;
    uploaderName: string;
    labels: string[];
    visibility: DocumentVisibility
}