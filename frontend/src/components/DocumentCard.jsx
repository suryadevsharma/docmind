import { useNavigate } from "react-router-dom";

export default function DocumentCard({ document, onDelete }) {
  const navigate = useNavigate();
  const uploaded = new Date(document.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="group relative rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur-md shadow-lg transition duration-300 hover:-translate-y-1 hover:border-slate-700/80 hover:bg-slate-800/40 hover:shadow-indigo-500/5 animate-fadeIn">
      <div className="mb-4 flex items-start justify-between gap-4">
        {/* Document Icon and details */}
        <div className="flex gap-3 min-w-0">
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor" className="h-6 w-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-base font-bold tracking-tight text-slate-100 group-hover:text-white" title={document.original_name}>
              {document.original_name}
            </h3>
            <span className="mt-1 inline-block rounded-md bg-slate-800/80 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-400 border border-slate-700/50">
              {document.file_type}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-2 space-y-1 text-xs text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-slate-500">Uploaded:</span>
          <span>{uploaded}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-slate-500">Document Size:</span>
          <span>{document.chunk_count} text blocks</span>
        </div>
      </div>

      <div className="mt-6 flex gap-2.5">
        <button
          onClick={() => navigate(`/chat/${document.id}`, { state: { document } })}
          className="flex-1 flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/10 transition hover:bg-indigo-500 hover:shadow-indigo-500/20 outline-none"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-3.5 w-3.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
          </svg>
          Chat RAG
        </button>
        <button
          onClick={() => {
            if (window.confirm("Are you sure you want to delete this document? All chat sessions and index history will be destroyed.")) {
              onDelete(document.id);
            }
          }}
          className="rounded-xl border border-rose-950/40 bg-rose-950/10 px-3 py-2 text-xs font-semibold text-rose-400 transition hover:bg-rose-950/40 hover:text-rose-300 outline-none"
          title="Delete Document"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
          </svg>
        </button>
      </div>
    </div>
  );
}
