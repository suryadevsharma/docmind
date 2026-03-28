import { useNavigate } from "react-router-dom";

export default function DocumentCard({ document, onDelete }) {
  const navigate = useNavigate();
  const uploaded = new Date(document.created_at).toLocaleString();

  return (
    <div className="rounded-xl bg-card p-4 shadow-md">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="truncate text-lg font-semibold">{document.original_name}</h3>
        <span className="rounded bg-slate-700 px-2 py-1 text-xs uppercase">{document.file_type}</span>
      </div>
      <p className="text-sm text-slate-300">Uploaded: {uploaded}</p>
      <p className="text-sm text-slate-300">Chunks: {document.chunk_count}</p>
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => navigate(`/chat/${document.id}`, { state: { document } })}
          className="flex-1 rounded bg-indigo-500 px-3 py-2 text-sm hover:bg-indigo-400"
        >
          Chat
        </button>
        <button
          onClick={() => {
            if (window.confirm("Delete this document?")) onDelete(document.id);
          }}
          className="rounded bg-rose-600 px-3 py-2 text-sm hover:bg-rose-500"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
