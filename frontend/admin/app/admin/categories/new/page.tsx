"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createCategory } from "../../../../lib/api";

export default function AdminCategoryNewPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    category: "",
    description: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createCategory({
        name: form.name,
        category: form.category,
        group: form.category,
        description: form.description,
      });
      router.push("/admin/categories");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Uložení selhalo";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">Přidat kategorii</h1>
          <p className="text-sm text-gray-500">Nová kategorie v administraci.</p>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div>
            <label className="mb-1 block text-sm font-medium">Název</label>
            <input
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="např. babka"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Kategorie (dříve Skupina)</label>
            <input
              type="text"
              name="category"
              value={form.category}
              onChange={handleChange}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="např. Rodina"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Popis</label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="volitelné"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => router.push("/admin/categories")}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700"
            >
              Zpět
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? "Ukládám..." : "Uložit"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}