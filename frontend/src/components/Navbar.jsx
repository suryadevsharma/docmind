import { Link } from "react-router-dom";

export default function Navbar() {
  const logout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/70 px-6 py-4 backdrop-blur-md shadow-lg">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <Link to="/" className="flex items-center gap-2 outline-none">
          <span className="bg-gradient-to-r from-indigo-400 to-violet-500 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent">
            DocMind
          </span>
          <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-400 border border-indigo-500/20">
            RAG Q&A
          </span>
        </Link>
        
        <button
          onClick={logout}
          className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-slate-300 transition duration-300 hover:border-slate-700 hover:bg-slate-800 hover:text-white focus:outline-none"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
