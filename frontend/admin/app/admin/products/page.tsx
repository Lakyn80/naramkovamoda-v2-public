
"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Category, Product } from "../../../lib/types";
import { deleteProduct, fetchCategories, fetchProducts, updateProduct } from "../../../lib/api";
import { resolveMediaUrl } from "../../../lib/media";
const PAGE_SIZE = 20;

type StockFilter = "all" | "in_stock" | "out_stock";

function formatPrice(value?: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(2)} Kč`;
}

function getStockBadge(stock?: number | null): { label: string; className: string } {
  if (stock === null || stock === undefined) {
    return { label: "—", className: "bg-gray-100 text-gray-600" };
  }
  if (stock > 5) {
    return { label: `Skladem: ${stock}`, className: "bg-emerald-500 text-white" };
  }
  if (stock > 0) {
    return { label: `Skladem: ${stock}`, className: "bg-amber-400 text-gray-900" };
  }
  return { label: "Vyprodáno", className: "bg-red-500 text-white" };
}

function ProductsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [activeError, setActiveError] = useState<string | null>(null);
  const [activeUpdatingId, setActiveUpdatingId] = useState<number | null>(null);

  const [query, setQuery] = useState(() => searchParams.get("search") || "");
  const [categoryId, setCategoryId] = useState(() => searchParams.get("category") || "");
  const [stockFilter, setStockFilter] = useState<StockFilter>(
    () => (searchParams.get("stock") as StockFilter) || "all"
  );
  const [page, setPage] = useState(() => {
    const raw = Number(searchParams.get("page") || "1");
    return Number.isFinite(raw) && raw > 0 ? raw : 1;
  });

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([fetchProducts(), fetchCategories()])
      .then(([productsData, categoriesData]) => {
        if (!active) return;
        setProducts(productsData);
        setCategories(categoriesData);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst produkty");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const nextQuery = searchParams.get("search") || "";
    const nextCategory = searchParams.get("category") || "";
    const nextStock = (searchParams.get("stock") as StockFilter) || "all";
    const rawPage = Number(searchParams.get("page") || "1");
    const nextPage = Number.isFinite(rawPage) && rawPage > 0 ? rawPage : 1;

    if (nextQuery !== query) setQuery(nextQuery);
    if (nextCategory !== categoryId) setCategoryId(nextCategory);
    if (nextStock !== stockFilter) setStockFilter(nextStock);
    if (nextPage !== page) setPage(nextPage);
  }, [searchParams, query, categoryId, stockFilter, page]);

  const updateUrl = (next: { search?: string; category?: string; stock?: StockFilter; page?: number }) => {
    const params = new URLSearchParams();
    const searchValue = next.search ?? query;
    const categoryValue = next.category ?? categoryId;
    const stockValue = next.stock ?? stockFilter;
    const pageValue = next.page ?? page;

    if (searchValue) params.set("search", searchValue);
    if (categoryValue) params.set("category", categoryValue);
    if (stockValue && stockValue !== "all") params.set("stock", stockValue);
    if (pageValue && pageValue > 1) params.set("page", String(pageValue));

    const queryString = params.toString();
    router.replace(queryString ? `?${queryString}` : "?", { scroll: false });
  };

  const filteredRows = useMemo(() => {
    let rows = [...products];
    const q = query.trim().toLowerCase();
    if (q) {
      rows = rows.filter((product) => product.name?.toLowerCase().includes(q));
    }

    const catId = Number(categoryId);
    if (Number.isFinite(catId) && catId > 0) {
      rows = rows.filter((product) => product.category_id === catId);
    }

    if (stockFilter === "in_stock") {
      rows = rows.filter((product) => (product.stock ?? 0) > 0);
    }

    if (stockFilter === "out_stock") {
      rows = rows.filter((product) => (product.stock ?? 0) <= 0);
    }

    rows.sort((a, b) => (b.id ?? 0) - (a.id ?? 0));

    return rows;
  }, [products, query, categoryId, stockFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filteredRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  useEffect(() => {
    if (page !== currentPage) {
      setPage(currentPage);
      updateUrl({ page: currentPage });
    }
  }, [page, currentPage]);

  const created = searchParams.get("created") === "1";

  const handleDelete = async (productId: number) => {
    const ok = window.confirm("Opravdu smazat tento produkt?");
    if (!ok) return;
    setDeleteError(null);
    setDeletingId(productId);
    try {
      await deleteProduct(productId);
      setProducts((prev) => prev.filter((p) => p.id !== productId));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Smazání selhalo";
      setDeleteError(message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleToggleActive = async (productId: number, nextActive: boolean) => {
    setActiveError(null);
    setActiveUpdatingId(productId);
    try {
      const formData = new FormData();
      formData.set("active", nextActive ? "1" : "0");
      const updated = await updateProduct(productId, formData);
      setProducts((prev) => prev.map((p) => (p.id === productId ? { ...p, ...updated } : p)));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Uložení selhalo";
      setActiveError(message);
    } finally {
      setActiveUpdatingId(null);
    }
  };

  const resetFilters = () => {
    setQuery("");
    setCategoryId("");
    setStockFilter("all");
    setPage(1);
    updateUrl({ search: "", category: "", stock: "all", page: 1 });
  };

  const handleFilterChange = (next: { search?: string; category?: string; stock?: StockFilter }) => {
    setPage(1);
    updateUrl({ ...next, page: 1 });
  };

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">📦 Produkty</h1>
            <p className="text-sm text-gray-500">Seznam produktů z API.</p>
          </div>
          <Link
            href="/admin/products/new"
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700"
          >
            ➕ Přidat produkt
          </Link>
        </div>

        {created && (
          <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            Produkt byl úspěšně vytvořen.
          </div>
        )}

        {deleteError && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {deleteError}
          </div>
        )}
        {activeError && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {activeError}
          </div>
        )}

        <div className="mb-4 rounded-2xl border border-gray-200 bg-gradient-to-br from-gray-50 to-slate-50 p-4 shadow-sm">
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Hledat název</label>
              <input
                type="text"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  handleFilterChange({ search: event.target.value });
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="např. křišťál"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Kategorie</label>
              <select
                value={categoryId}
                onChange={(event) => {
                  setCategoryId(event.target.value);
                  handleFilterChange({ category: event.target.value });
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">— Všechny —</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {(category.group || "—") + " — " + category.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase text-gray-500">Sklad</label>
              <select
                value={stockFilter}
                onChange={(event) => {
                  setStockFilter(event.target.value as StockFilter);
                  handleFilterChange({ stock: event.target.value as StockFilter });
                }}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="all">Vše</option>
                <option value="in_stock">Skladem</option>
                <option value="out_stock">Vyprodáno</option>
              </select>
            </div>
            <div className="flex items-end gap-2">
              <button
                type="button"
                onClick={resetFilters}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                Reset filtrů
              </button>
              <div className="text-xs text-gray-500">{filteredRows.length} produktů</div>
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

        {!loading && !error && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-100 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Název</th>
                  <th className="px-4 py-3">Kategorie</th>
                  <th className="px-4 py-3">Cena</th>
                  <th className="px-4 py-3">Sklad</th>
                  <th className="px-4 py-3">Obrázek</th>
                  <th className="px-4 py-3">Média</th>
                  <th className="px-4 py-3">Akce</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {pageItems.map((product) => {
                  const imageUrl = resolveMediaUrl(product.image_url);
                  const mediaCount = product.media?.length ?? 0;
                  const badge = getStockBadge(product.stock);
                  const stockValue = Number(product.stock ?? 0);
                  const isOutOfStock = !Number.isFinite(stockValue) || stockValue <= 0;
                  const isActive = product.active !== false && !isOutOfStock;
                  return (
                    <tr key={product.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-600">{product.id}</td>
                      <td className="px-4 py-3 font-medium">{product.name}</td>
                      <td className="px-4 py-3">{product.category_name ?? "—"}</td>
                      <td className="px-4 py-3">{formatPrice(product.price)}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs ${badge.className}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {imageUrl ? (
                          <div className="h-14 w-14 overflow-hidden rounded-lg shadow">
                            <img src={imageUrl} alt={product.name} className="h-full w-full object-cover" />
                          </div>
                        ) : (
                          <div className="h-14 w-14 rounded-lg bg-gray-100" />
                        )}
                      </td>
                      <td className="px-4 py-3">{mediaCount} souborů</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Link
                            href={`/admin/products/${product.id}/edit`}
                            className="rounded-md border border-gray-300 px-3 py-1 text-xs hover:bg-gray-100"
                          >
                            Upravit
                          </Link>
                          <button
                            type="button"
                            onClick={() => handleDelete(product.id)}
                            disabled={deletingId === product.id}
                            className="rounded-md border border-red-200 px-3 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-60"
                          >
                            {deletingId === product.id ? "Mažu..." : "Smazat"}
                          </button>
                          <label className="flex items-center gap-2 text-xs text-gray-700">
                            <input
                              type="checkbox"
                              checked={isActive}
                              disabled={activeUpdatingId === product.id || isOutOfStock}
                              onChange={(e) => handleToggleActive(product.id, e.target.checked)}
                            />
                            Aktivní
                          </label>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && totalPages > 1 && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
            <div>
              Stránka {currentPage} / {totalPages} · Zobrazeno {pageItems.length} z {filteredRows.length}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  const nextPage = Math.max(1, currentPage - 1);
                  setPage(nextPage);
                  updateUrl({ page: nextPage });
                }}
                disabled={currentPage <= 1}
                className="rounded-md border border-gray-300 px-3 py-1 disabled:opacity-50"
              >
                Předchozí
              </button>
              <button
                type="button"
                onClick={() => {
                  const nextPage = Math.min(totalPages, currentPage + 1);
                  setPage(nextPage);
                  updateUrl({ page: nextPage });
                }}
                disabled={currentPage >= totalPages}
                className="rounded-md border border-gray-300 px-3 py-1 disabled:opacity-50"
              >
                Další
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default function AdminProductsPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-gray-50 text-gray-900">
          <div className="mx-auto max-w-6xl px-6 py-10">
            <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
              Načítání...
            </div>
          </div>
        </main>
      }
    >
      <ProductsContent />
    </Suspense>
  );
}
