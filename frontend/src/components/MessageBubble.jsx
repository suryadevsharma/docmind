import ReactMarkdown from "react-markdown";

export default function MessageBubble({ message, sources = [] }) {
  const isUser = message.role === "user";
  
  // Normalize sources format
  const normalizedSources = (sources || []).map((s) => {
    if (typeof s === "string") {
      return { text: s, page: null, source: "Document" };
    }
    return s;
  });

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fadeIn`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-md transition-all duration-300 ${
          isUser
            ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-br-none shadow-indigo-900/10"
            : "bg-slate-800/60 border border-slate-700/40 backdrop-blur-sm text-slate-100 rounded-bl-none shadow-black/10"
        }`}
      >
        <div className="prose prose-invert text-sm max-w-none leading-relaxed">
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown className="markdown">{message.content}</ReactMarkdown>
          )}
        </div>

        {!isUser && normalizedSources.length > 0 && (
          <div className="mt-3.5 border-t border-slate-700/40 pt-2.5">
            <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-400">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="h-3 w-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
              </svg>
              Sources & Citations
            </div>
            
            <div className="mt-2 flex flex-wrap gap-2">
              {normalizedSources.map((source, idx) => (
                <details
                  key={idx}
                  className="group rounded-xl border border-slate-700/50 bg-slate-900/40 p-2 text-xs transition-all duration-300 hover:border-indigo-500/50 hover:bg-slate-900/90"
                >
                  <summary className="flex cursor-pointer items-center justify-between gap-3 font-medium text-slate-300 outline-none select-none list-none">
                    <span className="truncate max-w-[150px] text-[10px] font-mono text-indigo-300">
                      {source.source}
                    </span>
                    {source.page && (
                      <span className="rounded bg-indigo-500/10 px-1.5 py-0.5 text-[9px] font-bold text-indigo-400">
                        Page {source.page}
                      </span>
                    )}
                  </summary>
                  <p className="mt-2 max-w-md border-t border-slate-800/80 pt-2 text-[11px] leading-relaxed text-slate-400">
                    {source.text}
                  </p>
                </details>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
