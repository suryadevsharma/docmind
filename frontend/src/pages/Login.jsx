import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/axios";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/api/auth/login", { email, password });
      localStorage.setItem("token", res.data.data.token);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[#020617] px-4 py-12">
      {/* Background Gradients */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(99,102,241,0.08),transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_70%,rgba(139,92,246,0.08),transparent_50%)]" />
      
      <form onSubmit={submit} className="relative z-10 w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/40 p-8 backdrop-blur-md shadow-2xl animate-fadeIn">
        <div className="mb-6 text-center">
          <h1 className="bg-gradient-to-r from-indigo-400 to-violet-500 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
            DocMind
          </h1>
          <p className="mt-2 text-xs text-slate-400">Sign in to your document workspace</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">Email Address</label>
            <input
              className="w-full rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-2.5 text-sm text-white outline-none transition duration-300 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">Password</label>
            <input
              className="w-full rounded-xl border border-slate-800 bg-slate-950/40 px-4 py-2.5 text-sm text-white outline-none transition duration-300 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-950 bg-rose-950/20 p-3 text-xs text-rose-400">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded-xl bg-indigo-600 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/15 hover:bg-indigo-500 hover:shadow-indigo-500/25 transition duration-300 disabled:cursor-not-allowed disabled:opacity-50 outline-none"
        >
          {loading ? "Signing In..." : "Sign In"}
        </button>

        <p className="mt-6 text-center text-xs text-slate-400">
          Don't have an account?{" "}
          <Link className="font-semibold text-indigo-400 hover:text-indigo-300 transition" to="/register">
            Create one
          </Link>
        </p>
      </form>
    </div>
  );
}
