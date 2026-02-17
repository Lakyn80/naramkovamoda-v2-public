"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Toast } from "../../../components/Toast";
import { loginAdmin } from "../../../lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginAdmin({ username, password });
      router.push("/admin/products");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Přihlášení selhalo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl bg-white/90 p-8 shadow-2xl backdrop-blur">
        <h1 className="mb-6 text-center text-2xl font-semibold">🔐 Přihlášení do administrace</h1>

        {error && (
          <div className="mb-4">
            <Toast message={error} tone="error" onClose={() => setError(null)} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium text-gray-700">
              Uživatelské jméno
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
              Heslo
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Přihlašuji…" : "Přihlásit se"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600">
          <a href="/admin/forgot" className="text-blue-600 hover:text-blue-700">
            Zapomenuté heslo?
          </a>
        </div>
      </div>
    </div>
  );
}
