import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams, Link } from "react-router-dom";
import api from "../api/axios";
import Navbar from "../components/Navbar";
import ChatWindow from "../components/ChatWindow";

export default function ChatPage() {
  const { documentId } = useParams();
  const { state } = useLocation();
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [document, setDocument] = useState(state?.document || null);
  const [error, setError] = useState("");

  const docTitle = useMemo(() => document?.original_name || `Document #${documentId}`, [document, documentId]);

  const fetchSessions = async () => {
    try {
      const res = await api.get(`/api/chat/sessions/${documentId}`);
      const list = res.data.data || [];
      setSessions(list);
      // Auto-set the active session to the first one if not set
      setActiveSession((prev) => {
        if (prev && list.some((s) => s.id === prev)) return prev;
        return list.length ? list[0].id : null;
      });
      setError("");
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to load sessions");
    }
  };

  const fetchDocument = async () => {
    try {
      const res = await api.get("/api/documents/");
      const match = (res.data.data || []).find((d) => String(d.id) === String(documentId));
      if (match) setDocument(match);
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to load document");
    }
  };

  useEffect(() => {
    fetchSessions();
    fetchDocument();
  }, [documentId]);

  const createSession = async () => {
    try {
      const res = await api.post("/api/chat/session", { document_id: Number(documentId) });
      const newSessionId = res.data.data.id;
      setActiveSession(newSessionId);
      await fetchSessions();
      setError("");
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to create session");
    }
  };

  const deleteSession = async (id) => {
    if (!window.confirm("Are you sure you want to delete this chat session?")) return;
    try {
      await api.delete(`/api/chat/session/${id}`);
      if (activeSession === id) {
        setActiveSession(null);
      }
      fetchSessions();
      setError("");
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to delete session");
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <Navbar />
      <main className="mx-auto flex max-w-7xl flex-col gap-6 p-4 lg:flex-row lg:p-6">
        {/* Sidebar */}
        <aside className="w-full flex-shrink-0 rounded-2xl border border-slate-800 bg-slate-900/40 p-4 backdrop-blur-md lg:w-80 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-md font-semibold tracking-wide text-indigo-400 uppercase">Chat Sessions</h2>
            <Link to="/" className="text-xs text-slate-400 hover:text-white transition">
              &larr; Back
            </Link>
          </div>
          
          <button
            onClick={createSession}
            className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/15 transition duration-300 hover:bg-indigo-500 hover:shadow-indigo-500/25"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-4 w-4">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Chat
          </button>

          <div className="space-y-1.5 max-h-[50vh] overflow-y-auto custom-scrollbar">
            {sessions.length === 0 ? (
              <p className="py-8 text-center text-xs text-slate-500">No sessions yet. Create one to begin.</p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  className={`group flex items-center justify-between rounded-xl p-1 transition ${
                    activeSession === s.id
                      ? "bg-indigo-600/95 text-white shadow-md shadow-indigo-600/10"
                      : "hover:bg-slate-800/40 text-slate-300"
                  }`}
                >
                  <button
                    onClick={() => setActiveSession(s.id)}
                    className="flex-1 px-3 py-2 text-left text-sm font-medium outline-none truncate"
                  >
                    Session #{s.id}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSession(s.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:bg-slate-700/50 hover:text-rose-400 transition duration-200"
                    title="Delete Chat Session"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Chat window panel */}
        <section className="flex-1 flex flex-col min-w-0">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="truncate text-xl font-bold tracking-tight text-slate-100" title={docTitle}>
              {docTitle}
            </h2>
            {document && (
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-indigo-300 border border-slate-700/60 uppercase">
                {document.file_type}
              </span>
            )}
          </div>
          
          {error && (
            <div className="mb-4 rounded-xl border border-rose-950 bg-rose-950/20 p-4 text-sm text-rose-300">
              {error}
            </div>
          )}

          {activeSession ? (
            <ChatWindow sessionId={activeSession} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/10 p-12 text-center text-slate-400 backdrop-blur-sm">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="mb-3 h-12 w-12 text-slate-500">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
              </svg>
              <h3 className="text-md font-semibold text-slate-200">Start a chat</h3>
              <p className="mt-1 text-sm text-slate-500">Create a new session to begin querying this document.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
