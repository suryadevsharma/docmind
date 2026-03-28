import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
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
      setActiveSession((prev) => prev || (list.length ? list[0].id : null));
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
      setActiveSession(res.data.data.id);
      fetchSessions();
      setError("");
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to create session");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto flex max-w-7xl flex-col gap-4 p-4 lg:flex-row">
        <aside className="w-full rounded-xl bg-surface p-3 lg:w-80">
          <h2 className="mb-2 text-lg font-semibold">Chats</h2>
          <button onClick={createSession} className="mb-3 w-full rounded bg-indigo-500 px-3 py-2 text-sm hover:bg-indigo-400">
            New Chat
          </button>
          <div className="space-y-2">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveSession(s.id)}
                className={`w-full rounded px-3 py-2 text-left text-sm ${activeSession === s.id ? "bg-indigo-500" : "bg-card"}`}
              >
                Session #{s.id}
              </button>
            ))}
          </div>
        </aside>
        <section className="flex-1">
          <h2 className="mb-3 text-xl font-semibold text-indigo-300">{docTitle}</h2>
          {error && <p className="mb-3 rounded bg-rose-900/40 p-3 text-sm text-rose-300">{error}</p>}
          {activeSession ? (
            <ChatWindow sessionId={activeSession} />
          ) : (
            <div className="rounded-xl bg-surface p-6 text-slate-300">Create a new chat session to begin.</div>
          )}
        </section>
      </main>
    </div>
  );
}
