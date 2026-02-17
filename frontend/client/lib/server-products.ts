import "server-only";

import type { Product } from "./types";
import { slugify } from "./slugify";
import { getCachedJson } from "./server-cache";

const BACKEND_URL = process.env.NMM_BACKEND_URL || "http://backend:8080";
const PRODUCTS_CACHE_TTL = Number(process.env.PRODUCTS_CACHE_TTL || "120");

async function fetchProducts(): Promise<Product[]> {
  const res = await fetch(`${BACKEND_URL}/api/products/`, { cache: "no-store" });
  if (!res.ok) {
    return [];
  }
  const items = (await res.json()) as Product[];
  return (items || []).filter((p) => p && p.active !== false && Number(p.stock ?? 0) > 0);
}

export async function fetchProductsCached(): Promise<Product[]> {
  return getCachedJson<Product[]>("products:list", PRODUCTS_CACHE_TTL, fetchProducts);
}

export async function fetchProductBySlugCached(slug: string): Promise<Product | null> {
  const items = await fetchProductsCached();
  return items.find((p) => slugify(p?.name || "") === slug || String(p.id) === slug) || null;
}
