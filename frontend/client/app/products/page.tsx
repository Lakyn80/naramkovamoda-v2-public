"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { Product } from "../../lib/types";
import { fetchProducts } from "../../lib/api";
import { resolveMediaUrl } from "../../lib/media";


function formatPrice(value?: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(2)} Kč`;
}

export default function ProductsPage() {
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
        setProducts(data);
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

  const rows = useMemo(() => products, [products]);

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
        <div className="mb-6">
          <h1 className="text-xl sm:text-2xl font-semibold">Produkty</h1>
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
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {rows.map((product) => {
              const imageUrl = resolveMediaUrl(product.image_thumb_url || product.image_url);
              return (
                <Link
                  key={product.id}
                  href={`/products/${product.id}`}
                  className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:border-gray-300"
                >
                  <div className="mb-3 h-48 w-full overflow-hidden rounded bg-gray-100">
                    {imageUrl ? (
                      <img src={imageUrl} alt={product.name} className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-xs text-gray-400">
                        Bez obrázku
                      </div>
                    )}
                  </div>
                  <div className="text-sm font-semibold">{product.name}</div>
                  <div className="text-sm text-gray-500">{formatPrice(product.price)}</div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
