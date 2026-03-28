import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/axios";

export default function Register() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/api/auth/register", {
        full_name: fullName,
        email,
        password,
      });
      localStorage.setItem("token", res.data.data.token);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.message || "Registration failed");
    }
  };

  return (
    <div className="grid min-h-screen place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-xl bg-surface p-6 shadow-lg">
        <h1 className="mb-5 text-2xl font-bold text-indigo-400">Create Account</h1>
        <input
          className="mb-3 w-full rounded bg-card px-3 py-2 outline-none"
          type="text"
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <input
          className="mb-3 w-full rounded bg-card px-3 py-2 outline-none"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="mb-3 w-full rounded bg-card px-3 py-2 outline-none"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="mb-3 text-sm text-rose-400">{error}</p>}
        <button className="w-full rounded bg-indigo-500 px-3 py-2 font-medium hover:bg-indigo-400">Sign Up</button>
        <p className="mt-4 text-sm text-slate-300">
          Have an account? <Link className="text-indigo-300" to="/login">Login</Link>
        </p>
      </form>
    </div>
  );
}
