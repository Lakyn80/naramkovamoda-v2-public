"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Toast } from "../../../components/Toast";
import { resetPassword } from "../../../lib/api";

function ResetContent() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (!token) {
      setError("Chybí token pro reset hesla.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword({ token, password, password2 });
      setSuccess("Heslo bylo nastaveno. Můžeš se přihlásit.");
      setTimeout(() => router.push("/admin/login"), 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset hesla selhal.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="mb-4 text-xl font-semibold">Nastavit nové heslo</h1>

        {(error || success) && (
          <div className="mb-4 space-y-2">
            {error && <Toast message={error} tone="error" onClose={() => setError(null)} />}
            {success && <Toast message={success} tone="success" onClose={() => setSuccess(null)} />}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
              Nové heslo
            </label>
            <input
              id="password"
              name="password"
              type="password"
              minLength={6}
              required
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="password2" className="mb-1 block text-sm font-medium text-gray-700">
              Potvrzení hesla
            </label>
            <input
              id="password2"
              name="password2"
              type="password"
              minLength={6}
              required
              autoComplete="new-password"
              value={password2}
              onChange={(event) => setPassword2(event.target.value)}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
          >
            {loading ? "Ukládám…" : "Uložit heslo"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600">
          <a href="/admin/forgot" className="text-blue-600 hover:text-blue-700">
            ← Zpět na obnovu
          </a>
        </div>
      </div>
    </div>
  );
}

export default function AdminResetPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center px-4 py-10">
          <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl text-sm text-gray-600">
            Načítání...
          </div>
        </div>
      }
    >
      <ResetContent />
    </Suspense>
  );
}
