"use client";

import { useState } from "react";
import { Toast } from "../../../components/Toast";
import { forgotPassword } from "../../../lib/api";

export default function AdminForgotPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await forgotPassword({ email });
      setSuccess("Odkaz na reset hesla byl odeslán.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Odeslání odkazu selhalo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="mb-2 text-xl font-semibold">Obnova hesla</h1>
        <p className="mb-6 text-sm text-gray-600">
          Zadej e-mail svého účtu. Pošleme ti odkaz na reset hesla.
        </p>

        {(error || success) && (
          <div className="mb-4 space-y-2">
            {error && <Toast message={error} tone="error" onClose={() => setError(null)} />}
            {success && <Toast message={success} tone="success" onClose={() => setSuccess(null)} />}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
              E-mail
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Odesílám…" : "Poslat odkaz"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600">
          <a href="/admin/login" className="text-blue-600 hover:text-blue-700">
            ← Zpět na přihlášení
          </a>
        </div>
      </div>
    </div>
  );
}
