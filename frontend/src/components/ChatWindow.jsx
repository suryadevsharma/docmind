import { useEffect, useRef, useState } from "react";
import api from "../api/axios";
import MessageBubble from "./MessageBubble";

export default function ChatWindow({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  const fetchHistory = async () => {
    try {
      const res = await api.get(`/api/chat/history/${sessionId}`);
      const normalized = (res.data.data || []).map((m) => ({ ...m, sources: [] }));
      setMessages(normalized);
      setError("");
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to load history");
    }
  };

  useEffect(() => {
    if (!sessionId) return;
    fetchHistory();
  }, [sessionId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    if (!input.trim() || !sessionId || loading) return;
    const text = input.trim();
    setInput("");
    setLoading(true);
    setError("");
    const optimistic = { id: `tmp-${Date.now()}`, role: "user", content: text };
    setMessages((prev) => [...prev, optimistic]);
    try {
      const res = await api.post("/api/chat/message", { session_id: sessionId, message: text });
      const answer = res.data.data.answer;
      const sources = res.data.data.sources || [];
      const answerId = `ai-${Date.now()}`;
      setMessages((prev) => [...prev, { id: answerId, role: "assistant", content: answer, sources }]);
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[75vh] flex-col rounded-xl bg-surface">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} sources={m.sources} />
        ))}
        {error && <div className="text-sm text-rose-400">{error}</div>}
        {loading && <div className="text-sm text-slate-300">Thinking...</div>}
        <div ref={endRef} />
      </div>
      <div className="flex gap-2 border-t border-slate-700 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question about the document..."
          className="flex-1 rounded-md bg-card px-3 py-2 outline-none ring-indigo-400 focus:ring"
        />
        <button
          onClick={send}
          disabled={loading}
          className="rounded-md bg-indigo-500 px-4 py-2 hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </div>
  );
}
