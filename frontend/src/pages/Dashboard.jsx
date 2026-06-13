import { useEffect, useState } from "react";
import api from "../api/axios";
import DocumentCard from "../components/DocumentCard";
import Navbar from "../components/Navbar";
import UploadModal from "../components/UploadModal";

function SkeletonCard() {
  return (
    <div className="h-44 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="flex gap-3">
        <div className="h-11 w-11 rounded-xl bg-slate-800" />
        <div className="flex-1 space-y-2 py-1">
          <div className="h-4 rounded bg-slate-800 w-3/4" />
          <div className="h-3 rounded bg-slate-800 w-1/4" />
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="h-3 rounded bg-slate-800 w-5/6" />
        <div className="h-3 rounded bg-slate-800 w-1/2" />
      </div>
      <div className="mt-6 flex gap-2">
        <div className="h-8 rounded bg-slate-800 flex-1" />
        <div className="h-8 rounded bg-slate-800 w-10" />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/documents/");
      setDocuments(res.data.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const deleteDoc = async (id) => {
    try {
      await api.delete(`/api/documents/${id}`);
      fetchDocs();
    } catch (e) {
      alert("Failed to delete document: " + (e?.response?.data?.message || e.message));
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <Navbar />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-slate-900 bg-slate-950/20 py-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(99,102,241,0.08),transparent_50%)]" />
        <div className="mx-auto max-w-7xl px-6 relative z-10">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight md:text-4xl bg-gradient-to-r from-slate-100 via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                Knowledge Base Workspace
              </h1>
              <p className="mt-2 text-sm md:text-base text-slate-400 max-w-xl">
                Upload PDFs and DOCX files. DocMind extracts, vectors, and chunks their content, allowing you to ask complex questions in real-time.
              </p>
            </div>
            <div>
              <button
                onClick={() => setOpen(true)}
                className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/25 transition duration-300 hover:bg-indigo-500 hover:shadow-indigo-500/35 focus:outline-none"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-4.5 w-4.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Upload Document
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Grid Content */}
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight text-slate-200">
            Uploaded Reference Files ({documents.length})
          </h2>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, idx) => (
              <SkeletonCard key={idx} />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-800 bg-slate-900/10 py-16 px-6 text-center text-slate-400 backdrop-blur-sm shadow-xl">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-900 text-slate-500 border border-slate-800">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-8 w-8 text-indigo-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10.5v6m3-3H9m4.06-7.19-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-slate-200">No documents found</h3>
            <p className="mt-1 text-sm text-slate-500 max-w-sm">
              Your workspace is empty. Upload your first PDF or Word document to get started.
            </p>
            <button
              onClick={() => setOpen(true)}
              className="mt-6 rounded-xl border border-indigo-500/20 bg-indigo-500/10 px-4 py-2.5 text-xs font-bold text-indigo-400 hover:bg-indigo-500/20 transition outline-none"
            >
              Upload Document
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 animate-fadeIn">
            {documents.map((doc) => (
              <DocumentCard key={doc.id} document={doc} onDelete={deleteDoc} />
            ))}
          </div>
        )}
      </main>

      <UploadModal open={open} onClose={() => setOpen(false)} onUploaded={fetchDocs} />
    </div>
  );
}
