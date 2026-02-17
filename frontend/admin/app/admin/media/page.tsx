"use client";

import { useEffect, useState } from "react";
import { fetchProducts } from "../../../lib/api";
import { resolveMediaUrl } from "../../../lib/media";
import type { Product } from "../../../lib/types";

export default function AdminMediaPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    fetchProducts()
      .then((data) => {
        if (!active) return;
        setProducts(data || []);
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

  const allMedia: {
    productId: number;
    productName: string;
    url: string;
    id?: number;
  }[] = [];

  products.forEach((p) => {
    const mainUrl = resolveMediaUrl(p.image_url);

    if (mainUrl) {
      allMedia.push({
        productId: p.id,
        productName: p.name || "—",
        url: mainUrl,
      });
    }

    (p.media_items ?? []).forEach((m) => {
      const url = resolveMediaUrl(m.url || m.filename || null);
      if (url) {
        allMedia.push({
          productId: p.id,
          productName: p.name || "—",
          url,
          id: m.id ?? undefined,
        });
      }
    });

    (p.media ?? []).forEach((m) => {
      const fallback = typeof m === "string" ? m : null;
      const url = resolveMediaUrl(fallback);
      if (url) {
        allMedia.push({
          productId: p.id,
          productName: p.name || "—",
          url,
        });
      }
    });
  });

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Média</h2>

      <p className="text-sm text-gray-600">
        Přehled obrázků a médií napojených na produkty. Smazání média zatím
        nelze provést z této stránky.
      </p>

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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {allMedia.map((m, i) => (
            <div
              key={`${m.productId}-${m.id ?? "main"}-${i}`}
              className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm"
            >
              <div className="mb-2 h-32 overflow-hidden rounded bg-gray-100">
                <img
                  src={m.url}
                  alt={m.productName}
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src =
                      "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23ddd' width='100' height='100'/%3E%3Ctext fill='%23999' x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='12'%3EError%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>

              <p className="truncate text-xs font-medium text-gray-700">
                {m.productName}
              </p>
              <p className="truncate text-xs text-gray-500">
                Produkt #{m.productId}
              </p>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && allMedia.length === 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
          Žádná média
        </div>
      )}
    </div>
  );
}


