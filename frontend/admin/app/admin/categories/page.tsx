
"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { Category } from "../../../lib/types";
import { deleteCategory, fetchCategories } from "../../../lib/api";

export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    fetchCategories()
      .then((data) => {
        if (!active) return;
        setCategories(data);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst kategorie");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const groupOptions = useMemo(() => {
    const values = categories
      .map((cat) => cat.group || cat.category)
      .filter((val): val is string => Boolean(val));
    return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, "cs"));
  }, [categories]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return categories.filter((category) => {
      const matchesQuery = q
        ? `${category.name ?? ""} ${category.description ?? ""}`.toLowerCase().includes(q)
        : true;
      const matchesGroup = group ? (category.group || category.category) === group : true;
      return matchesQuery && matchesGroup;
    });
  }, [categories, group, query]);

  const handleDelete = async (categoryId: number) => {
    const ok = window.confirm("Smazat kategorii?");
    if (!ok) return;
    setDeleteError(null);
    setDeletingId(categoryId);
    try {
      await deleteCategory(categoryId, false);
      setCategories((prev) => prev.filter((cat) => cat.id !== categoryId));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Smazání selhalo";
      if (message.includes("Kategorie obsahuje produkty")) {
        const force = window.confirm(
          "Kategorie obsahuje produkty. Smazat kategorii včetně všech produktů?"
        );
        if (force) {
          try {
            await deleteCategory(categoryId, true);
            setCategories((prev) => prev.filter((cat) => cat.id !== categoryId));
            setDeletingId(null);
            return;
          } catch (forceErr) {
            const forceMessage =
              forceErr instanceof Error ? forceErr.message : "Hromadné smazání selhalo";
            setDeleteError(forceMessage);
          }
        } else {
          setDeleteError(message);
        }
      } else {
        setDeleteError(message);
      }
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Kategorie</h2>
          <p className="text-sm text-gray-500">Správa názvů, skupin a popisů kategorií.</p>
        </div>
        <Link
          href="/admin/categories/new"
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-semibold text-white"
        >
          + Přidat kategorii
        </Link>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Hledat</label>
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Název nebo popis"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Skupina</label>
            <select
              value={group}
              onChange={(event) => setGroup(event.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Všechny skupiny</option>
              {groupOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setGroup("");
              }}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              Reset
            </button>
            <div className="text-xs text-gray-500">{rows.length} záznamů</div>
          </div>
        </div>
      </div>

      {loading && (
        <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
          Načítání...
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-600">
          {error}
        </div>
      )}

      {deleteError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-600">
          {deleteError}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
              <tr>
                <th className="px-4 py-3">Název</th>
                <th className="px-4 py-3">Skupina</th>
                <th className="px-4 py-3">Popis</th>
                <th className="px-4 py-3">Akce</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {rows.map((category) => (
                <tr key={category.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{category.name}</td>
                  <td className="px-4 py-3 text-gray-600">{category.group || category.category || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{category.description || ""}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/admin/categories/${category.id}/edit`}
                        className="rounded-md border border-gray-300 px-3 py-1 text-xs hover:bg-gray-100"
                      >
                        Upravit
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleDelete(category.id)}
                        disabled={deletingId === category.id}
                        className="rounded-md border border-red-200 px-3 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-60"
                      >
                        {deletingId === category.id ? "Mažu..." : "Smazat"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                    Žádné kategorie
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
