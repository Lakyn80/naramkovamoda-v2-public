import type { MetadataRoute } from "next";

import { slugify } from "../lib/slugify";
import { fetchProductsCached } from "../lib/server-products";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  process.env.SITE_URL ||
  "http://localhost:3002";

export const runtime = "nodejs";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = SITE_URL.replace(/\/$/, "");
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [
    { url: `${base}/`, lastModified: now },
    { url: `${base}/shop`, lastModified: now },
    { url: `${base}/products`, lastModified: now },
  ];

  try {
    const items = await fetchProductsCached();
    items.forEach((p) => {
      if (!p?.name) return;
      const slug = slugify(p.name);
      entries.push({ url: `${base}/products/${slug}`, lastModified: now });
    });
  } catch {
    // ignore
  }

  return entries;
}
