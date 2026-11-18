
import type { Document } from '../types/document'

export const mockDocuments: Document[] = [
  {
    id: '1',
    name: 'Project documentation',
    type: 'pdf',
    category: 'Development',
    uploadedAt: '2026-11-15',
    uploaderId: 'user1',
    uploaderName: 'Alice',
    labels: ['documentation', 'project'],
    visibility: 'public',
  },
  {
    id: '2',
    name: 'Meeting notes',
    type: 'text',
    category: 'Meetings',
    uploadedAt: '2026-11-16',
    uploaderId: 'user1',
    uploaderName: 'Alice',
    labels: ['notes'],
    visibility: 'private',
  },
  {
    id: '3',
    name: 'Architecture diagram',
    type: 'image',
    category: 'Development',
    uploadedAt: '2026-11-17',
    uploaderId: 'user2',
    uploaderName: 'Bob',
    labels: ['architecture', 'diagram'],
    visibility: 'public',
  },
];
