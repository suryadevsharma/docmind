import { useRef, useState } from "react";
import api from "../api/axios";

export default function UploadModal({ open, onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  if (!open) return null;

  const validate = (f) => {
    const allowed = [".pdf", ".docx"];
    const ok = allowed.some((ext) => f.name.toLowerCase().endsWith(ext));
    if (!ok) throw new Error("Only .pdf and .docx file formats are allowed");
  };

  const upload = async () => {
    if (!file) return;
    setError("");
    setSuccess("");
    try {
      validate(file);
      const form = new FormData();
      form.append("file", file);
      await api.post("/api/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          const percent = Math.round((e.loaded / (e.total || 1)) * 100);
          setProgress(percent);
        },
      });
      setSuccess("Document uploaded and indexed successfully!");
      setFile(null);
      setProgress(0);
      onUploaded();
      // Auto close after 1.5s on success
      setTimeout(() => {
        onClose();
        setSuccess("");
      }, 1500);
    } catch (e) {
      setError(e?.response?.data?.message || e.message || "Document upload failed");
      setProgress(0);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight text-white">Upload Reference Document</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition outline-none">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-5 w-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            const dropped = e.dataTransfer.files?.[0];
            if (dropped) setFile(dropped);
          }}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-300 ${
            isDragOver
              ? "border-indigo-500 bg-indigo-500/5 shadow-inner"
              : file
              ? "border-emerald-500/50 bg-emerald-500/5"
              : "border-slate-700 bg-slate-950/40 hover:border-slate-600 hover:bg-slate-950/60"
          }`}
        >
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-slate-400 group-hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor" className="h-6 w-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-300">
            Drag and drop your file here, or <span className="text-indigo-400 hover:underline">browse</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Supports PDF & DOCX (Max 10MB)</p>
          
          {file && (
            <div className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-slate-800 px-3 py-2 text-xs font-semibold text-indigo-300 border border-indigo-500/10">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-3.5 w-3.5 flex-shrink-0">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
              <span className="truncate max-w-[250px]">{file.name}</span>
            </div>
          )}
        </div>
        
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        {progress > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 mb-1">
              <span>Uploading & Parsing...</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
              <div className="h-full bg-gradient-to-r from-indigo-500 to-violet-600 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-xl border border-rose-950 bg-rose-950/20 p-3 text-xs text-rose-400">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 rounded-xl border border-emerald-950 bg-emerald-950/20 p-3 text-xs text-emerald-400">
            {success}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white transition duration-300 outline-none"
          >
            Cancel
          </button>
          <button
            onClick={upload}
            disabled={!file || progress > 0}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/15 hover:bg-indigo-500 hover:shadow-indigo-500/25 transition duration-300 disabled:cursor-not-allowed disabled:opacity-40 outline-none"
          >
            Start Upload
          </button>
        </div>
      </div>
    </div>
  );
}
