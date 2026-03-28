export default function Navbar() {
  const logout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-700 bg-surface px-4 py-3">
      <h1 className="text-xl font-semibold text-indigo-400">DocMind</h1>
      <button onClick={logout} className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-medium hover:bg-indigo-400">
        Logout
      </button>
    </header>
  );
}
