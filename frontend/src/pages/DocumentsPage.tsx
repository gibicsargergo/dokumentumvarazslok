import { mockDocuments } from "../lib/documentsStub";

export default function DocumentsPage() {
  // Temporary user until authentication is implemented
  const currentUser = {
    id: 'user1',
    isAdmin: false,
  };

  const visibleDocuments = mockDocuments.filter(
    (doc) =>
      doc.visibility === 'public' ||
      doc.uploaderId === currentUser.id
  );

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="mb-6 text-3xl font-semibold">
        Documents
      </h1>

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
              const isOwner =
                doc.uploaderId === currentUser.id;

              const canEdit =
                isOwner || currentUser.isAdmin;

              return (
                <tr key={doc.id} className="border-t border-line">
                  <td className="p-4">{doc.name}</td>
                  <td className="p-4">{doc.type}</td>
                  <td className="p-4">{doc.category}</td>
                  <td className="p-4">{doc.uploadedAt}</td>
                  <td className="p-4">
                    {isOwner ? doc.uploaderName : '—'}
                  </td>
                  <td className="p-4">
                    {doc.labels.join(', ')}
                  </td>
                  <td className="p-4">{doc.visibility}</td>
                  <td className="p-4">
                    {canEdit && (
                      <button
                        type="button"
                        disabled
                        className="text-subtle"
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
    </main>
  );
}