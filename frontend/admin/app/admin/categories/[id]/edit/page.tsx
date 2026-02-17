"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchCategory, updateCategory } from "../../../../../lib/api";

export default function AdminCategoryEditPage() {
  const params = useParams();
  const router = useRouter();
  const categoryId = Number(Array.isArray(params?.id) ? params.id[0] : params?.id);

  const [form, setForm] = useState({
    name: "",
    category: "",
    description: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!categoryId) return;
    let active = true;
    setLoading(true);
    setError(null);

    fetchCategory(categoryId)
      .then((data) => {
        if (!active) return;
        setForm({
          name: data.name || "",
          category: data.group || data.category || "",
          description: data.description || "",
        });
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst kategorii");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [categoryId]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryId) return;
    setSaving(true);
    setError(null);
    try {
      await updateCategory(categoryId, {
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

  if (loading) {
    return (
      <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
        Načítání...
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">Upravit kategorii</h1>
          <p className="text-sm text-gray-500">ID #{categoryId}</p>
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
              {saving ? "Ukládám..." : "Uložit změny"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
