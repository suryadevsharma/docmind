import { useRef, useState } from "react";
import api from "../api/axios";

export default function UploadModal({ open, onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const inputRef = useRef(null);

  if (!open) return null;

  const validate = (f) => {
    const allowed = [".pdf", ".docx"];
    const ok = allowed.some((ext) => f.name.toLowerCase().endsWith(ext));
    if (!ok) throw new Error("Only .pdf and .docx are allowed");
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
      setSuccess("Upload successful");
      setFile(null);
      onUploaded();
    } catch (e) {
      setError(e?.response?.data?.message || e.message || "Upload failed");
    }
  };

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/60 p-4">
      <div className="w-full max-w-lg rounded-xl bg-surface p-5">
        <h2 className="mb-4 text-lg font-semibold">Upload Document</h2>
        <div
          className="cursor-pointer rounded-lg border-2 border-dashed border-slate-600 p-8 text-center"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const dropped = e.dataTransfer.files?.[0];
            if (dropped) setFile(dropped);
          }}
        >
          <p className="text-slate-300">Drag and drop or click to select PDF/DOCX</p>
          {file && <p className="mt-2 text-indigo-300">{file.name}</p>}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        {progress > 0 && (
          <div className="mt-3 h-2 rounded bg-card">
            <div className="h-2 rounded bg-indigo-500" style={{ width: `${progress}%` }} />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
        {success && <p className="mt-3 text-sm text-emerald-400">{success}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded bg-slate-700 px-3 py-2 text-sm">
            Close
          </button>
          <button onClick={upload} className="rounded bg-indigo-500 px-3 py-2 text-sm hover:bg-indigo-400">
            Upload
          </button>
        </div>
      </div>
    </div>
  );
}
