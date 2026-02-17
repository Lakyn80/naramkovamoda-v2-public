"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { fetchProducts } from "../../../lib/api";
import { useCart } from "../../../context/CartContext";
import { slugify } from "../../../lib/slugify";
import { emojify } from "../../../lib/emojify";
import { absoluteUploadUrl } from "../../../lib/media";
import { formatWristSize, normalizeWristSize } from "../../../lib/wrist-size";
import type { Product, ProductVariant } from "../../../lib/types";

interface VariantOption extends ProductVariant {
  isBase?: boolean;
}

const stripPopisPrefix = (value: string) => String(value || "").replace(/^popis:\s*/i, "").trim();
const EMOJI_SPLIT_RE =
  /(\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*)/gu;

const splitEmoji = (value: string) => {
  if (!value) return [];
  return value.split(EMOJI_SPLIT_RE).filter(Boolean);
};

const isEmojiPart = (value: string) => {
  if (!value) return false;
  const re = /(\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*)/u;
  return re.test(value);
};

const renderTitleWithEmoji = (value: string) =>
  splitEmoji(value).map((part, idx) => {
    const emoji = isEmojiPart(part);
    return (
      <span key={`${part}-${idx}`} className={emoji ? "notranslate text-beige-700" : ""}>
        {part}
      </span>
    );
  });

export default function ProductDetailClient({ slug }: { slug: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addToCart } = useCart();

  const slugParam = slug;
  const variantParam = searchParams.get("variant");
  const wristParam = searchParams.get("wrist") || searchParams.get("wrist_size");
  const normalizedWristParam = normalizeWristSize(wristParam);

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [photoIndex, setPhotoIndex] = useState(0);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [variantsOpen, setVariantsOpen] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  // Load product
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    fetchProducts()
      .then((data) => {
        if (!active) return;
        const found = (data || []).find(
          (p) => slugify(p?.name || "") === slugParam || String(p.id) === slugParam
        );
        if (found) {
          const price =
            typeof found.price === "number"
              ? found.price
              : typeof found.price_czk === "number"
              ? found.price_czk
              : Number(found.price) || 0;

          const foundActive = found.active !== false;
          const foundStock = Number(found.stock ?? 0);
          if (!foundActive || foundStock <= 0) {
            setProduct(null);
            return;
          }

          const normalizeImageUrl = (u: string | null | undefined) => absoluteUploadUrl(u);

          const variants = Array.isArray(found.variants)
            ? found.variants.map((v) => ({
                ...v,
                image_full_url: normalizeImageUrl(v.image_full_url || v.image_url || v.image),
                image_thumb_url: normalizeImageUrl(v.image_thumb_url || v.image_url || v.image),
                image_url: normalizeImageUrl(v.image_full_url || v.image_url || v.image),
                image: normalizeImageUrl(v.image_full_url || v.image || v.image_url),
                media: Array.isArray(v.media)
                  ? v.media.map((m) => ({
                      ...m,
                      image_full_url: normalizeImageUrl(m.image_full_url || m.image_url || m.image),
                      image_thumb_url: normalizeImageUrl(m.image_thumb_url || m.image_url || m.image),
                      image_url: normalizeImageUrl(m.image_full_url || m.image_url || m.image),
                    }))
                  : [],
              }))
            : [];

          const baseMediaRaw = Array.isArray(found.media)
            ? found.media
            : Array.isArray(found.images)
            ? found.images
            : [];
          const baseMedia = baseMediaRaw.map(normalizeImageUrl).filter(Boolean) as string[];

          const baseImages = [
            normalizeImageUrl(found.image_full_url || found.image_url || found.image),
            ...baseMedia,
          ]
            .filter(Boolean)
            .filter((v, i, a) => a.indexOf(v) === i) as string[];

          setProduct({
            ...found,
            stock: Number(found.stock ?? 0),
            price,
            image_url: baseImages[0] || null,
            images: baseImages,
            media: baseMedia,
            variants,
          });
        } else {
          setProduct(null);
        }
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message || "Nepodařilo se načíst produkt");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [slugParam]);

  // Build variant options
  const variantOptions = useMemo((): VariantOption[] => {
    if (!product) return [];

    const basePrice = Number(product.price ?? product.price_czk ?? 0);
    const baseImage =
      (Array.isArray(product.images) ? product.images[0] : null) || product.image_url;

    const baseVariant: VariantOption = {
      id: -1, // Use -1 for base
      variant_name: product.name || "Původní varianta",
      wrist_size: "",
      image_url: baseImage,
      image: baseImage,
      media: [],
      stock: Number(product.stock ?? 0),
      isBase: true,
      price_czk: basePrice,
      description: product.description || "",
    };

    const normalizedVariants: VariantOption[] = Array.isArray(product.variants)
      ? product.variants.map((v) => ({
          ...v,
          image_full_url: v.image_full_url || v.image_url || v.image,
          image_thumb_url: v.image_thumb_url || v.image_url || v.image,
          image_url: v.image_full_url || v.image_url || v.image,
          stock: Number(v.stock ?? 0),
          price_czk: Number(v.price_czk ?? v.price ?? product.price ?? 0),
          description: v.description || "",
        }))
      : [];

    return [baseVariant, ...normalizedVariants];
  }, [product]);

  // Select variant from URL params
  useEffect(() => {
    if (!variantOptions.length) return;

    const hasSelected =
      !!selectedVariantId &&
      variantOptions.some((v) => String(v.id) === String(selectedVariantId));
    const hasParams = Boolean(variantParam || normalizedWristParam);

    if (!hasParams && hasSelected) {
      return;
    }

    const next =
      (variantParam
        ? variantOptions.find((v) => String(v.id) === String(variantParam))
        : undefined) ||
      (normalizedWristParam
        ? variantOptions.find(
            (v) => normalizeWristSize(v.wrist_size) === normalizedWristParam
          )
        : undefined) ||
      (hasSelected
        ? variantOptions.find((v) => String(v.id) === String(selectedVariantId))
        : undefined) ||
      variantOptions[0];

    if (next && String(next.id) !== String(selectedVariantId)) {
      setSelectedVariantId(String(next.id));
      setVariantsOpen(false);
    }
  }, [variantOptions, variantParam, normalizedWristParam, selectedVariantId]);

  const selectedVariant = useMemo(
    () => variantOptions.find((v) => String(v.id) === String(selectedVariantId)) || null,
    [variantOptions, selectedVariantId]
  );

  const activePrice = useMemo(() => {
    if (selectedVariant) {
      const priceVal = selectedVariant.price_czk ?? selectedVariant.price;
      const parsed = Number(priceVal);
      if (Number.isFinite(parsed)) return parsed;
    }
    const fallback = Number(product?.price ?? product?.price_czk);
    return Number.isFinite(fallback) ? fallback : 0;
  }, [selectedVariant, product]);

  const activeDescription = useMemo(() => {
    const raw = selectedVariant?.description || product?.description || "";
    return stripPopisPrefix(raw);
  }, [selectedVariant, product]);

  const renderDescription = (rawText: string) => {
    const lines = rawText.split(/\r?\n/);
    const nodes: React.ReactNode[] = [];
    let listItems: string[] = [];
    let listMode = false;

    const flushList = () => {
      if (!listItems.length) return;
      const items = listItems;
      listItems = [];
      listMode = false;
      nodes.push(
        <ul key={`list-${nodes.length}`} className="product-description-list">
          {items.map((item, idx) => (
            <li key={`li-${nodes.length}-${idx}`}>{emojify(item)}</li>
          ))}
        </ul>
      );
    };

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        continue;
      }
      if (trimmed.endsWith(":")) {
        flushList();
        nodes.push(
          <h3 key={`h-${nodes.length}`} className="product-description-heading">
            {emojify(trimmed)}
          </h3>
        );
        listMode = true;
        continue;
      }
      if (trimmed.startsWith("-")) {
        listMode = true;
        listItems.push(trimmed.replace(/^\-\s*/, "").trim());
        continue;
      }
      if (listMode && trimmed.includes(":")) {
        flushList();
        nodes.push(
          <p key={`p-${nodes.length}`} className="product-description-paragraph">
            {emojify(trimmed)}
          </p>
        );
        continue;
      }
      if (listMode) {
        listItems.push(trimmed);
        continue;
      }
      flushList();
      nodes.push(
        <p key={`p-${nodes.length}`} className="product-description-paragraph">
          {emojify(trimmed)}
        </p>
      );
    }
    flushList();
    return nodes;
  };

  const baseImages = useMemo(() => {
    if (!product) return [];
    const baseList = Array.isArray(product.images) ? product.images : [];
    const fallback = product.image_url ? [product.image_url] : [];
    return Array.from(new Set([...fallback, ...baseList].filter(Boolean)));
  }, [product]);

  const displayImages = useMemo(() => {
    if (!product) return [];

    if (selectedVariant && !selectedVariant.isBase) {
      const variantImages: string[] = [];
      const preferred = selectedVariant.image_full_url || selectedVariant.image_url || selectedVariant.image;
      if (preferred) variantImages.push(preferred);

      if (Array.isArray(selectedVariant.media)) {
        selectedVariant.media.forEach((m) => {
          const img = typeof m === "string" ? m : m?.image_full_url || m?.image_url;
          if (img) variantImages.push(img);
        });
      }

      return Array.from(new Set(variantImages.filter(Boolean)));
    }

    return baseImages;
  }, [product, selectedVariant, baseImages]);

  useEffect(() => {
    if (!displayImages.length) {
      setPhotoIndex(0);
      return;
    }
    const preferred = selectedVariant?.image_full_url || selectedVariant?.image_url || selectedVariant?.image;
    if (preferred) {
      const idx = displayImages.indexOf(preferred);
      if (idx !== -1) {
        setPhotoIndex(idx);
        return;
      }
    }
    setPhotoIndex((idx) => Math.min(idx, displayImages.length - 1));
  }, [displayImages, selectedVariant]);

  const handleAddToCart = () => {
    const activeStock =
      typeof selectedVariant?.stock === "number" && Number.isFinite(selectedVariant.stock)
        ? selectedVariant.stock
        : Number(product?.stock);
    if (!product || activeStock === 0) return;

    const activeVariant = selectedVariant || variantOptions[0] || null;
    const isBase = activeVariant?.isBase;

    const variantPayload =
      activeVariant && !isBase
        ? {
            variantId: activeVariant.id,
            variantName: activeVariant.variant_name || undefined,
            wristSize: activeVariant.wrist_size || undefined,
            image: activeVariant.image_url || activeVariant.image,
            stock: activeStock,
          }
        : {};

    addToCart({
      id: product.id,
      name: product.name,
      price: activePrice,
      quantity: 1,
      image: variantPayload.image || product.image_url || undefined,
      stock: activeStock,
      ...variantPayload,
    });
  };

  if (loading) {
    return (
      <section className="pt-28 pb-12 bg-gradient-to-br from-beige-300 to-beige-200 min-h-screen flex items-center justify-center">
        <div className="text-center text-lg text-beige-900">Načítám...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="pt-28 pb-12 bg-gradient-to-br from-beige-300 to-beige-200 min-h-screen flex items-center justify-center">
        <div className="text-center text-lg text-red-600">{error}</div>
      </section>
    );
  }

  if (!product) {
    return (
      <section className="pt-28 pb-12 bg-gradient-to-br from-beige-300 to-beige-200 min-h-screen flex items-center justify-center">
        <div className="text-center text-lg text-beige-900">
          Produkt nenalezen.{" "}
          <Link href="/shop" className="underline">
            Zpět do obchodu
          </Link>
        </div>
      </section>
    );
  }

  const activeStock =
    typeof selectedVariant?.stock === "number" && Number.isFinite(selectedVariant.stock)
      ? selectedVariant.stock
      : Number(product.stock);
  const out = activeStock === 0;
  const displayWristSize = formatWristSize(selectedVariant?.wrist_size || product.wrist_size);
  const displayName = emojify(selectedVariant?.variant_name || product.name);
  const titleText = `${displayName}${displayWristSize ? ` - ${displayWristSize}` : ""}`;

  return (
    <section className="pt-24 sm:pt-28 pb-12 bg-gradient-to-br from-beige-300 to-beige-200 min-h-screen">
      <div className="container mx-auto max-w-4xl px-4 sm:px-6 md:px-8">
        <nav className="mb-3 text-sm text-beige-900/80">
          <span className="font-semibold">{displayName}</span>
        </nav>
        <div className="mb-4">
          <button
            type="button"
            onClick={() => router.back()}
            className="inline-flex items-center gap-2 text-beige-800 font-semibold hover:underline"
          >
            ← Zpět do obchodu
          </button>
        </div>

        <div className="bg-white/20 backdrop-blur-lg rounded-2xl shadow-2xl p-6 border border-white/40">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            {/* Images */}
            <div className="space-y-4 relative">
              <div className="absolute top-2 left-2 z-10">
                {out ? (
                  <span className="px-2 py-1 text-xs font-semibold rounded bg-red-600/90 text-white">
                    Vyprodáno
                  </span>
                ) : (
                  <span className="px-2 py-1 text-xs font-semibold rounded bg-emerald-600/90 text-white">
                    Skladem: {activeStock}
                  </span>
                )}
              </div>

              {displayImages[photoIndex] ? (
                <img
                  src={displayImages[photoIndex]}
                  alt={product.name}
                  className="w-full h-[260px] sm:h-[300px] md:h-[360px] object-cover rounded-xl shadow-lg cursor-pointer transition-transform duration-300 hover:scale-[1.02]"
                  onClick={() => displayImages.length && setLightboxOpen(true)}
                />
              ) : (
                <div className="w-full h-[260px] sm:h-[300px] md:h-[360px] rounded-xl bg-white/10" />
              )}

              <div className="flex gap-2 flex-wrap justify-center sm:justify-start">
                {displayImages.map((img, i) => (
                  <img
                    key={i}
                    src={img}
                    alt={`${product.name} ${i + 1}`}
                    onClick={() => setPhotoIndex(i)}
                    className={`h-16 w-16 sm:h-20 sm:w-20 object-cover rounded-lg cursor-pointer border-2 ${
                      photoIndex === i ? "border-beige-500 shadow-lg" : "border-transparent"
                    } transition duration-300 hover:scale-105`}
                  />
                ))}
              </div>
            </div>

            {/* Details */}
            <div className="flex flex-col justify-center">
              <h2 className="text-2xl sm:text-3xl font-extrabold bg-gradient-to-r from-beige-600 to-beige-700 bg-clip-text text-transparent drop-shadow-lg">
                {renderTitleWithEmoji(titleText)}
              </h2>

              <p className="text-xl font-semibold text-beige-700 mt-2 drop-shadow-sm">
                {activePrice.toFixed(2)} Kč
              </p>

              {/* Variant selector */}
              {variantOptions.length > 1 && (
                <div className="mt-4 relative">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Vyberte variantu
                  </label>

                  <button
                    type="button"
                    onClick={() => setVariantsOpen((v) => !v)}
                    className="w-full border border-amber-300 rounded-xl bg-gradient-to-r from-stone-100 to-amber-50 px-4 py-3 shadow-sm hover:shadow-md flex items-center justify-between gap-3 transition"
                  >
                    <div className="flex items-center gap-3 text-left">
                      {(selectedVariant?.image_thumb_url || selectedVariant?.image_url) && (
                        <img
                          src={selectedVariant.image_thumb_url || selectedVariant.image_url || ""}
                          alt={selectedVariant.variant_name || "Varianta"}
                          className="w-12 h-12 object-cover rounded-lg border border-amber-200"
                        />
                      )}
                      <div>
                        <div className="text-sm font-semibold text-gray-900">
                          {selectedVariant?.variant_name || "Varianta"}
                        </div>
                        {formatWristSize(selectedVariant?.wrist_size) && (
                          <div className="text-xs text-gray-600">
                            {formatWristSize(selectedVariant?.wrist_size)}
                          </div>
                        )}
                        {typeof selectedVariant?.stock === "number" && (
                          <div className="text-xs text-emerald-700">
                            Skladem: {selectedVariant.stock}
                          </div>
                        )}
                      </div>
                    </div>
                    <span className="text-amber-700 text-lg">{variantsOpen ? "▲" : "▼"}</span>
                  </button>

                  {variantsOpen && (
                    <div className="absolute z-30 mt-2 w-full rounded-xl border border-amber-200 bg-white shadow-xl max-h-64 overflow-auto">
                      {variantOptions.map((v) => {
                        const active = String(v.id) === String(selectedVariantId);
                        return (
                          <button
                            type="button"
                            key={v.id}
                            onClick={() => {
                              setSelectedVariantId(String(v.id));
                              setVariantsOpen(false);
                            }}
                            className={`w-full px-4 py-3 flex items-center gap-3 text-left transition ${
                              active
                                ? "bg-gradient-to-r from-amber-100 to-orange-50 border-l-4 border-amber-500"
                                : "hover:bg-amber-50"
                            }`}
                          >
                            {(v.image_thumb_url || v.image_url) && (
                              <img
                                src={v.image_thumb_url || v.image_url || ""}
                                alt={v.variant_name || "Varianta"}
                                className="w-10 h-10 object-cover rounded-md border border-amber-100"
                              />
                            )}
                            <div className="text-sm font-medium text-gray-900">
                              {v.variant_name || "Varianta"}
                              {formatWristSize(v.wrist_size) && (
                                <span className="text-xs text-gray-600 block">
                                  {formatWristSize(v.wrist_size)}
                                </span>
                              )}
                              {typeof v.stock === "number" && (
                                <span className="text-[11px] text-emerald-700 block">
                                  Skladem: {v.stock}
                                </span>
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              <div className="mt-3 product-description">
                {renderDescription(activeDescription || "Detail produktu zde.")}
              </div>

              <button
                onClick={handleAddToCart}
                disabled={out}
                className={`mt-6 py-2 px-5 rounded-lg shadow-lg transition-transform transform hover:-translate-y-0.5 ${
                  out
                    ? "bg-gray-400 cursor-not-allowed text-white"
                    : "bg-gradient-to-r from-beige-600 to-beige-700 hover:from-beige-700 hover:to-beige-800 text-white"
                }`}
                title={out ? "Produkt je vyprodán" : "Přidat do košíku"}
              >
                {out ? "Vyprodáno" : "Přidat do košíku"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Simple lightbox */}
      {lightboxOpen && displayImages.length > 0 && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4 sm:p-6"
          onClick={() => setLightboxOpen(false)}
        >
          <button
            className="absolute top-4 right-4 sm:top-6 sm:right-6 text-white text-2xl sm:text-3xl p-2 -m-2 z-10"
            onClick={() => setLightboxOpen(false)}
            aria-label="Zavřít"
          >
            ×
          </button>
          <button
            className="absolute left-2 sm:left-4 top-1/2 -translate-y-1/2 text-white text-2xl sm:text-3xl p-3 rounded-full bg-black/40 hover:bg-black/60 transition z-10"
            onClick={(e) => {
              e.stopPropagation();
              setPhotoIndex((i) => (i > 0 ? i - 1 : displayImages.length - 1));
            }}
            aria-label="Předchozí obrázek"
          >
            ‹
          </button>
          <img
            src={displayImages[photoIndex]}
            alt={product.name}
            className="max-h-[85vh] sm:max-h-[90vh] max-w-[calc(100vw-5rem)] sm:max-w-[90vw] w-auto h-auto object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            className="absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 text-white text-2xl sm:text-3xl p-3 rounded-full bg-black/40 hover:bg-black/60 transition z-10"
            onClick={(e) => {
              e.stopPropagation();
              setPhotoIndex((i) => (i < displayImages.length - 1 ? i + 1 : 0));
            }}
            aria-label="Další obrázek"
          >
            ›
          </button>
        </div>
      )}
    </section>
  );
}
