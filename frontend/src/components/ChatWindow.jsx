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
      setMessages(res.data.data || []);
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

    // optimistic user message
    const userMsgId = `tmp-user-${Date.now()}`;
    const userMsg = { id: userMsgId, role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);

    // placeholder assistant message
    const aiMsgId = `tmp-ai-${Date.now()}`;
    const placeholderAiMsg = { id: aiMsgId, role: "assistant", content: "", sources: [] };
    setMessages((prev) => [...prev, placeholderAiMsg]);

    try {
      const token = localStorage.getItem("token");
      const baseUrl = api.defaults.baseURL || "";
      const response = await fetch(`${baseUrl}/api/chat/message/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ session_id: sessionId, message: text })
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.detail || errJson?.message || "Failed to start streaming response");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulatedAnswer = "";
      let retrievedSources = [];
      let buffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          buffer += decoder.decode(value, { stream: !done });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const lines = part.split("\n");
            for (const line of lines) {
              if (line.trim().startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.trim().slice(6));
                  if (data.type === "sources") {
                    retrievedSources = data.sources || [];
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === aiMsgId ? { ...msg, sources: retrievedSources } : msg
                      )
                    );
                  } else if (data.type === "content") {
                    accumulatedAnswer += data.content;
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === aiMsgId ? { ...msg, content: accumulatedAnswer } : msg
                      )
                    );
                  } else if (data.type === "error") {
                    setError(data.message || "An error occurred during generation");
                  }
                } catch (e) {
                  // Ignore parsing errors
                }
              }
            }
          }
        }
      }
    } catch (e) {
      setError(e.message || "Failed to get response");
      // Clean up empty placeholder if it failed completely
      setMessages((prev) => prev.filter((msg) => msg.id !== aiMsgId || msg.content.length > 0));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[75vh] flex-col rounded-2xl border border-slate-800/80 bg-slate-900/60 backdrop-blur-xl shadow-2xl">
      {/* Conversation Thread */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4 custom-scrollbar">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-slate-400">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="mb-2 h-10 w-10 text-indigo-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
            </svg>
            <p className="text-sm font-medium">No messages yet. Start by asking a question below!</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} sources={m.sources} />
        ))}
        {error && (
          <div className="rounded-xl border border-rose-950 bg-rose-950/20 px-4 py-3 text-sm text-rose-400">
            {error}
          </div>
        )}
        {loading && (
          <div className="flex items-center gap-2 text-indigo-400">
            <div className="flex space-x-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.3s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.15s]"></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-indigo-400"></div>
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider">AI is generating response...</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Form */}
      <div className="border-t border-slate-800/80 bg-slate-950/40 p-4">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask a question about this document..."
            className="flex-1 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2.5 text-sm text-white outline-none transition duration-300 placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <button
            onClick={send}
            disabled={loading}
            className="flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition duration-300 hover:bg-indigo-500 hover:shadow-indigo-500/35 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
