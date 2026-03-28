import ReactMarkdown from "react-markdown";

export default function MessageBubble({ message, sources = [] }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] rounded-xl px-4 py-3 ${isUser ? "bg-indigo-500" : "bg-slate-800"}`}>
        {isUser ? <p>{message.content}</p> : <ReactMarkdown>{message.content}</ReactMarkdown>}
        {!isUser && sources?.length > 0 && (
          <details className="mt-2 text-sm text-slate-300">
            <summary className="cursor-pointer text-indigo-300">Sources</summary>
            <ul className="mt-2 list-disc pl-5">
              {sources.map((source, idx) => (
                <li key={idx}>{source}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
