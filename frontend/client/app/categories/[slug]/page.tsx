"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { Category } from "../../../lib/types";
import { fetchCategoryBySlug } from "../../../lib/api";
import { resolveMediaUrl } from "../../../lib/media";
import { slugify } from "../../../lib/slugify";


function formatPrice(value?: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(2)} Kč`;
}

export default function CategoryDetailPage() {
  const params = useParams();
  const slugParam = Array.isArray(params?.slug) ? params.slug[0] : params?.slug;
  const [category, setCategory] = useState<Category | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slugParam) return;
    let active = true;
    setLoading(true);
    setError(null);

    fetchCategoryBySlug(slugParam)
      .then((data) => {
        if (!active) return;
        setCategory(data);
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
  }, [slugParam]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 text-gray-900">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
          <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
            Načítání...
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-gray-50 text-gray-900">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
          <div className="rounded-md border border-red-200 bg-red-50 p-6 text-sm text-red-600">
            {error}
          </div>
        </div>
      </main>
    );
  }

  if (!category) {
    return (
      <main className="min-h-screen bg-gray-50 text-gray-900">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
          <div className="rounded-md border border-gray-200 bg-white p-6 text-sm text-gray-600">
            Kategorie nenalezena. <Link href="/" className="underline">Zpět domů</Link>
          </div>
        </div>
      </main>
    );
  }

  const products = category.products ?? [];

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
        <h1 className="text-xl sm:text-2xl font-semibold">{category.name}</h1>
        {category.description && (
          <p className="mt-2 text-sm text-gray-600">{category.description}</p>
        )}

        <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => {
            const imageUrl = resolveMediaUrl(product.image_thumb_url || product.image_url);
            return (
              <Link
                key={product.id}
                href={`/products/${slugify(product.name)}`}
                className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:border-gray-300"
              >
                <div className="mb-3 h-40 w-full overflow-hidden rounded bg-gray-100">
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
      </div>
    </main>
  );
}
