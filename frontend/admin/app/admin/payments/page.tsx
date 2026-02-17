"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { deleteOrder, fetchPayments, fetchPaymentsSummary, updatePaymentStatus } from "../../../lib/api";
import type { PaymentItem, PaymentSummary } from "../../../lib/types";

function formatPrice(value?: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${Number(value).toFixed(2)} Kč`;
}

function PaymentsContent() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<PaymentItem[]>([]);
  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const statusFilter = searchParams.get("status") || "all";
  const vsFilter = searchParams.get("vs") || "";

  const statusLabels: Record<string, string> = {
    paid: "Zaplaceno",
    awaiting_payment: "Čeká na platbu",
    canceled: "Zrušeno",
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchPayments({ status: statusFilter !== "all" ? statusFilter : undefined, limit: 100 }),
      fetchPaymentsSummary(),
    ])
      .then(([paymentsData, summaryData]) => {
        if (!active) return;
        setItems(paymentsData.items || []);
        setSummary(summaryData || null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst platby");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [statusFilter, vsFilter]);

  const updateUrl = (params: Record<string, string>) => {
    const p = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v && v !== "all") p.set(k, v);
    });
    window.location.search = p.toString();
  };

  const handleStatusChange = async (orderId: number, nextStatus: string) => {
    setUpdateError(null);
    setUpdatingId(orderId);
    try {
      await updatePaymentStatus(orderId, nextStatus);
      setItems((prev) =>
        prev.map((p) =>
          String(p.id) === String(orderId) ? { ...p, status: nextStatus } : p
        )
      );
    } catch (err) {
      setUpdateError(err instanceof Error ? err.message : "Uložení selhalo");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDeleteOrder = async (orderId: number) => {
    if (!window.confirm(`Opravdu smazat objednávku #${orderId}?`)) return;
    setUpdateError(null);
    setDeletingId(orderId);
    try {
      await deleteOrder(orderId);
      const [paymentsData, summaryData] = await Promise.all([
        fetchPayments({ status: statusFilter !== "all" ? statusFilter : undefined, limit: 100 }),
        fetchPaymentsSummary(),
      ]);
      setItems(paymentsData.items || []);
      setSummary(summaryData || null);
    } catch (err) {
      setUpdateError(err instanceof Error ? err.message : "Smazání selhalo");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Platby</h2>

      {summary && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
          Počet: <strong>{summary.count ?? 0}</strong> | Celkem:{" "}
          <strong>{formatPrice(summary.total_amount ?? 0)}</strong>
        </div>
      )}

      <div className="flex flex-wrap gap-4 rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Stav:</label>
          <select
            value={statusFilter}
            onChange={(e) => updateUrl({ status: e.target.value })}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="all">Vše</option>
            <option value="paid">Zaplaceno</option>
            <option value="awaiting_payment">Čeká na platbu</option>
            <option value="canceled">Zrušeno</option>
          </select>
        </div>
      </div>

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
      {updateError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {updateError}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-2 text-left font-semibold">ID</th>
                <th className="px-4 py-2 text-left font-semibold">VS</th>
                <th className="px-4 py-2 text-right font-semibold">Částka</th>
                <th className="px-4 py-2 text-left font-semibold">Stav</th>
                <th className="px-4 py-2 text-left font-semibold">Datum</th>
                <th className="px-4 py-2 text-left font-semibold">Potvrdit</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p, i: number) => (
                <tr key={p.id ?? i} className="border-b border-gray-100">
                  <td className="px-4 py-2">{String(p.id ?? "-")}</td>
                  <td className="px-4 py-2">{String(p.vs ?? p.variable_symbol ?? "-")}</td>
                  <td className="px-4 py-2 text-right">
                    {formatPrice(p.amount_czk ?? p.amount ?? p.total_amount)}
                  </td>
                  <td className="px-4 py-2">
                    {statusLabels[String(p.status ?? "")] || String(p.status ?? "-")}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    {p.received_at
                      ? String(p.received_at).slice(0, 16).replace("T", " ")
                      : p.created_at
                      ? String(p.created_at).slice(0, 16).replace("T", " ")
                      : "-"}
                  </td>
                  <td className="px-4 py-2">
                    {p.id && (
                      <div className="flex items-center gap-2">
                        <select
                          value={String(p.status ?? "awaiting_payment")}
                          onChange={(e) => handleStatusChange(Number(p.id), e.target.value)}
                          disabled={updatingId === Number(p.id) || deletingId === Number(p.id)}
                          className="rounded border border-gray-300 px-2 py-1 text-xs"
                        >
                          <option value="paid">Zaplaceno</option>
                          <option value="awaiting_payment">Čeká na platbu</option>
                          <option value="canceled">Zrušeno</option>
                        </select>
                        <button
                          type="button"
                          onClick={() => handleDeleteOrder(Number(p.id))}
                          disabled={deletingId === Number(p.id) || updatingId === Number(p.id)}
                          className="rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-60"
                        >
                          {deletingId === Number(p.id) ? "Mažu..." : "Smazat"}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && (
            <div className="p-8 text-center text-gray-500">Žádné platby</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminPaymentsPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
          Načítání...
        </div>
      }
    >
      <PaymentsContent />
    </Suspense>
  );
}





