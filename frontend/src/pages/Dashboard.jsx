import { useEffect, useState } from "react";
import api from "../api/axios";
import DocumentCard from "../components/DocumentCard";
import Navbar from "../components/Navbar";
import UploadModal from "../components/UploadModal";

function SkeletonCard() {
  return <div className="h-36 animate-pulse rounded-xl bg-slate-800" />;
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
    await api.delete(`/api/documents/${id}`);
    fetchDocs();
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-6xl p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Your Documents</h2>
          <button onClick={() => setOpen(true)} className="rounded bg-indigo-500 px-3 py-2 hover:bg-indigo-400">
            Upload Document
          </button>
        </div>
        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, idx) => (
              <SkeletonCard key={idx} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
