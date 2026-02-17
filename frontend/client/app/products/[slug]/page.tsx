import type { Metadata } from "next";

import { slugify } from "../../../lib/slugify";
import { fetchProductBySlugCached } from "../../../lib/server-products";
import ProductDetailClient from "./ProductDetailClient";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  process.env.SITE_URL ||
  "http://localhost:3002";

export const runtime = "nodejs";

function toAbsoluteUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  const base = SITE_URL.replace(/\/$/, "");
  if (value.startsWith("/")) return `${base}${value}`;
  return `${base}/static/uploads/${value}`;
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const slug = params.slug;
  const product = await fetchProductBySlugCached(slug);
  if (!product) {
    return {
      title: "Produkt nenalezen",
      description: "Produkt nebyl nalezen.",
    };
  }

  const title = product.seo_title || product.name || "Produkt";
  const descSource = product.seo_description || product.description || "";
  const description =
    descSource.length > 160 ? `${descSource.slice(0, 159).trim()}…` : descSource;
  const canonical = `${SITE_URL.replace(/\/$/, "")}/products/${slugify(product.name || slug)}`;
  const rawImage = product.image_full_url || product.image_url || product.image || "/logo.jpg";
  const imageUrl = toAbsoluteUrl(rawImage);
  const stock = Number(product.stock ?? 0);
  const hasImage = Boolean(product.image_full_url || product.image_url || product.image);
  const shouldIndex = hasImage && stock > 0;

  return {
    title,
    description,
    robots: shouldIndex
      ? undefined
      : {
          index: false,
          follow: false,
          googleBot: {
            index: false,
            follow: false,
          },
        },
    alternates: { canonical },
    openGraph: {
      title,
      description,
      url: canonical,
      images: imageUrl ? [{ url: imageUrl }] : undefined,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: imageUrl ? [imageUrl] : undefined,
    },
  };
}

export default function ProductDetailPage({ params }: { params: { slug: string } }) {
  const slug = params.slug;
  return (
    <>
      {/* JSON-LD is rendered server-side for SEO */}
      <ProductJsonLd slug={slug} />
      <ProductDetailClient slug={slug} />
    </>
  );
}

async function ProductJsonLd({ slug }: { slug: string }) {
  const product = await fetchProductBySlugCached(slug);
  if (!product) return null;

  const canonical = `${SITE_URL.replace(/\/$/, "")}/products/${slugify(product.name || slug)}`;
  const rawImage = product.image_full_url || product.image_url || product.image || "/logo.jpg";
  const imageUrl = toAbsoluteUrl(rawImage);
  const description = (product.seo_description || product.description || "").trim();
  const price = Number(product.price ?? product.price_czk);
  const stock = Number(product.stock ?? 0);

  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.seo_title || product.name || "Produkt",
    description,
    image: imageUrl ? [imageUrl] : undefined,
    sku: String(product.id),
    url: canonical,
  };

  if (Number.isFinite(price) && price > 0) {
    jsonLd.offers = {
      "@type": "Offer",
      priceCurrency: "CZK",
      price: price.toFixed(2),
      availability: stock > 0 ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
      url: canonical,
    };
  }

  return (
    // eslint-disable-next-line @next/next/no-sync-scripts
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
