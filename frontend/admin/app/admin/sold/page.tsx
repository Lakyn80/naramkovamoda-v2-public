"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { SoldRow, SoldSummary } from "../../../lib/types";
import {
  buildInvoicePreviewUrl,
  buildSoldExportUrl,
  fetchSold,
  sendInvoiceEmail,
} from "../../../lib/api";

function formatPrice(value?: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${Number(value).toFixed(2)} Kč`;
}

function SoldContent() {
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<SoldRow[]>([]);
  const [summary, setSummary] = useState<SoldSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sendingId, setSendingId] = useState<number | null>(null);

  const fromDate = searchParams.get("from") || "";
  const toDate = searchParams.get("to") || "";

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    fetchSold({ from: fromDate, to: toDate })
      .then((data) => {
        if (!active) return;
        setRows(data.rows || []);
        setSummary(data.summary || null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst prodané");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fromDate, toDate]);

  const applyFilters = (from: string, to: string) => {
    const params = new URLSearchParams();
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    const qs = params.toString();
    window.location.href = qs ? `/admin/sold?${qs}` : "/admin/sold";
  };

  const handleSendInvoice = async (soldId: number) => {
    setSendingId(soldId);
    try {
      await sendInvoiceEmail(soldId);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Odeslání selhalo");
    } finally {
      setSendingId(null);
    }
  };

  const exportXlsxUrl = buildSoldExportUrl("xlsx", { from: fromDate, to: toDate });
  const exportPdfUrl = buildSoldExportUrl("pdf", { from: fromDate, to: toDate });

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Prodané</h2>

      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Od:</label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => applyFilters(e.target.value, toDate)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Do:</label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => applyFilters(fromDate, e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={() => applyFilters("", "")}
          className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50"
        >
          Reset
        </button>
        <a
          href={exportXlsxUrl}
          target="_blank"
          rel="noreferrer"
          className="rounded border border-emerald-300 bg-emerald-50 px-3 py-1 text-sm text-emerald-700 hover:bg-emerald-100"
        >
          Export Excel
        </a>
        <a
          href={exportPdfUrl}
          target="_blank"
          rel="noreferrer"
          className="rounded border border-blue-300 bg-blue-50 px-3 py-1 text-sm text-blue-700 hover:bg-blue-100"
        >
          Export PDF
        </a>
      </div>

      {summary && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
          Počet: <strong>{summary.count ?? 0}</strong> | Celkem:{" "}
          <strong>{formatPrice(summary.total_amount ?? 0)}</strong>
        </div>
      )}

      {loading && (
        <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
          Načítání...
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-2 text-left font-semibold">ID</th>
                <th className="px-4 py-2 text-left font-semibold">Produkt</th>
                <th className="px-4 py-2 text-right font-semibold">Ks</th>
                <th className="px-4 py-2 text-right font-semibold">Cena/ks</th>
                <th className="px-4 py-2 text-right font-semibold">Celkem</th>
                <th className="px-4 py-2 text-left font-semibold">Email</th>
                <th className="px-4 py-2 text-left font-semibold">VS</th>
                <th className="px-4 py-2 text-left font-semibold">Datum</th>
                <th className="px-4 py-2 text-left font-semibold">Akce</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id ?? Math.random()} className="border-b border-gray-100">
                  <td className="px-4 py-2">{r.id}</td>
                  <td className="px-4 py-2">{r.product_name ?? "-"}</td>
                  <td className="px-4 py-2 text-right">{r.quantity ?? 0}</td>
                  <td className="px-4 py-2 text-right">
                    {formatPrice(r.unit_price_czk ?? r.unit_price ?? r.price_czk)}
                  </td>
                  <td className="px-4 py-2 text-right">{formatPrice(r.total_czk)}</td>
                  <td className="px-4 py-2 text-xs">{r.customer_email ?? "-"}</td>
                  <td className="px-4 py-2">{r.vs ?? "-"}</td>
                  <td className="px-4 py-2 text-xs">
                    {r.sold_at ? r.sold_at.slice(0, 16).replace("T", " ") : "-"}
                  </td>
                  <td className="px-4 py-2">
                    {r.id && (
                      <span className="flex gap-1">
                        <a
                          href={buildInvoicePreviewUrl(r.id)}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          Faktura
                        </a>
                        <button
                          type="button"
                          onClick={() => handleSendInvoice(r.id!)}
                          disabled={sendingId === r.id}
                          className="text-emerald-600 hover:underline disabled:opacity-50"
                        >
                          {sendingId === r.id ? "Odesílám..." : "E-mail"}
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && (
            <div className="p-8 text-center text-gray-500">Žádné prodané položky</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminSoldPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
          Načítání...
        </div>
      }
    >
      <SoldContent />
    </Suspense>
  );
}
