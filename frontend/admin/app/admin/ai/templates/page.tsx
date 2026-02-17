"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchAiTemplates, fetchProducts, storeAiTemplate } from "../../../../lib/api";
import type { AiTemplateItem, Product } from "../../../../lib/types";

export default function AdminAiTemplatesPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [templates, setTemplates] = useState<AiTemplateItem[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isTransientFetchError = (err: unknown) => {
    if (!(err instanceof Error)) return false;
    const msg = err.message || "";
    return /failed to fetch|networkerror|load failed/i.test(msg);
  };

  const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

  const showNotice = (msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 2000);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const fetchAll = async () => {
      const [productsRes, templatesRes] = await Promise.allSettled([
        fetchProducts(),
        fetchAiTemplates(),
      ]);

      if (productsRes.status === "rejected") {
        console.warn("AI Templates: fetchProducts failed", productsRes.reason);
      }
      if (templatesRes.status === "rejected") {
        console.warn("AI Templates: fetchAiTemplates failed", templatesRes.reason);
      }

      if (productsRes.status === "rejected") {
        throw productsRes.reason;
      }
      if (templatesRes.status === "rejected") {
        throw templatesRes.reason;
      }

      setProducts(productsRes.value || []);
      setTemplates(templatesRes.value || []);
    };
    try {
      await fetchAll();
    } catch (err) {
      if (isTransientFetchError(err)) {
        try {
          await sleep(500);
          await fetchAll();
        } catch (retryErr) {
          setError(retryErr instanceof Error ? retryErr.message : "Načtení selhalo");
        }
      } else {
        setError(err instanceof Error ? err.message : "Načtení selhalo");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const productOptions = useMemo(
    () =>
      products.map((p) => ({
        id: p.id,
        label: `${p.name} (#${p.id})`,
      })),
    [products]
  );

  const handleStoreTemplate = async () => {
    if (!selectedProductId) {
      setError("Vyber produkt.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await storeAiTemplate(Number(selectedProductId));
      setSelectedProductId("");
      await loadData();
      showNotice("Vzor uložen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Uložení selhalo");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">AI šablony</h2>
        <p className="text-sm text-gray-600">Uložení produktů jako vzory pro budoucí generování.</p>
      </div>

      {notice && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          {notice}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <select
            className="min-w-[240px] rounded-md border border-gray-300 px-3 py-2 text-sm"
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            disabled={loading}
          >
            <option value="">— vyber produkt —</option>
            {productOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleStoreTemplate}
            disabled={saving}
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {saving ? "Ukládám..." : "Uložit vzor"}
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700">Uložené vzory</h3>
        {loading && <div className="mt-3 text-sm text-gray-500">Načítání...</div>}
        {!loading && templates.length === 0 && (
          <div className="mt-3 text-sm text-gray-500">Žádné vzory.</div>
        )}
        {!loading && templates.length > 0 && (
          <div className="mt-3 overflow-hidden rounded-md border border-gray-100">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Název</th>
                  <th className="px-3 py-2">Typ</th>
                  <th className="px-3 py-2">Cena</th>
                  <th className="px-3 py-2">Vytvořeno</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((tpl) => (
                  <tr key={tpl.id} className="border-t">
                    <td className="px-3 py-2 text-xs text-gray-600">{tpl.id}</td>
                    <td className="px-3 py-2">{tpl.title || "—"}</td>
                    <td className="px-3 py-2">{tpl.product_type || "—"}</td>
                    <td className="px-3 py-2">{tpl.price_czk ?? "—"}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{tpl.created_at || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
