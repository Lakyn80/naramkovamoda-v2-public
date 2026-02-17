"use client";

import React, { Suspense, useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchCategories, fetchProducts } from "../../lib/api";
import { useCart } from "../../context/CartContext";
import { slugify } from "../../lib/slugify";
import { emojify } from "../../lib/emojify";
import { absoluteUploadUrl } from "../../lib/media";
import { formatWristSize, normalizeWristSize, wristSizeToNumber } from "../../lib/wrist-size";
import { useScrollResetOnChange } from "../../lib/useScrollReset";
import type { Category, Product } from "../../lib/types";

const COLS = 3;
const ROWS = 8;
const PAGE_SIZE = COLS * ROWS;

function getPageList(current: number, total: number): (number | string)[] {
  const delta = 1;
  const range: number[] = [];
  const rangeWithDots: (number | string)[] = [];
  let l: number | undefined;

  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - delta && i <= current + delta)) {
      range.push(i);
    }
  }

  for (const i of range) {
    if (l) {
      if (i - l === 2) {
        rangeWithDots.push(l + 1);
      } else if (i - l > 2) {
        rangeWithDots.push("…");
      }
    }
    rangeWithDots.push(i);
    l = i;
  }

  return rangeWithDots;
}

interface MappedProduct extends Product {
  image: string | null;
  category_key: string;
}

function compareWristSizes(a: string, b: string): number {
  const numA = wristSizeToNumber(a);
  const numB = wristSizeToNumber(b);
  if (numA !== null && numB !== null && numA !== numB) {
    return numA - numB;
  }
  if (numA !== null && numB === null) return -1;
  if (numA === null && numB !== null) return 1;
  return a.localeCompare(b);
}

function getPrimaryWristSize(product: Product): string {
  const direct = normalizeWristSize(product.wrist_size);
  if (direct) return direct;
  const fromVariants = (product.variants || [])
    .map((v) => normalizeWristSize(v.wrist_size))
    .filter(Boolean);
  if (!fromVariants.length) return "";
  return fromVariants.sort(compareWristSizes)[0] || "";
}

function buildDescriptionPreview(description?: string | null): string {
  const raw = String(description || "").replace(/\s+/g, " ").trim();
  if (!raw) return "";
  const cleaned = raw.replace(/^popis:\s*/i, "").trim();
  if (!cleaned) return "";
  const words = cleaned.split(" ").filter(Boolean);
  const limit = 55;
  const preview = words.slice(0, limit).join(" ");
  const needsEllipsis = words.length > limit;
  return `${preview}${needsEllipsis ? "..." : "..."}`;
}

function ShopPageContent() {
  const { addToCart } = useCart();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<MappedProduct[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [wristFilter, setWristFilter] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useScrollResetOnChange(searchParams.toString());

  // Load categories
  useEffect(() => {
    fetchCategories()
      .then((data) => {
        const mapped = (data || []).map((cat) => ({
          ...cat,
          slug: cat.slug || slugify(cat.name || ""),
          key: `${cat.slug || slugify(cat.name || "")}-${cat.id}`,
        }));
        setCategories(mapped);
      })
      .catch((err) => console.error("Chyba při načtení kategorií:", err));
  }, []);

  // Load products
  useEffect(() => {
    setLoading(true);
    fetchProducts()
      .then((data) => {
        const mapped: MappedProduct[] = (data || []).map((p) => {
          const priceNumber =
            typeof p.price === "number"
              ? p.price
              : typeof p.price_czk === "number"
              ? p.price_czk
              : Number(p.price) || 0;

          const categorySlug = p.category_slug || slugify(p.category_name || "");
          const categoryKey = `${categorySlug}-${p.category_id || p.id}`;

          return {
            ...p,
            image: absoluteUploadUrl(p.image_thumb_url || p.image_url || p.image),
            price: priceNumber,
            stock: Number(p.stock ?? 0),
            category_key: categoryKey,
          };
        });
        setProducts(mapped);
      })
      .catch((err) => console.error("Chyba načtení produktů:", err))
      .finally(() => setLoading(false));
  }, []);

  // Sync with URL params
  useEffect(() => {
    const rawCats = searchParams.get("categories");
    if (rawCats) {
      const parsed = rawCats.split(",").map((v) => v.trim()).filter(Boolean);
      setSelectedCategories(parsed);
    } else {
      setSelectedCategories([]);
    }
    setSearchTerm(searchParams.get("q") || "");
    setSortBy(searchParams.get("sort") || "");
    setWristFilter(normalizeWristSize(searchParams.get("wrist") || ""));
    const pageParam = parseInt(searchParams.get("page") || "1", 10);
    setPage(Number.isFinite(pageParam) && pageParam > 0 ? pageParam : 1);
  }, [searchParams]);

  const applyFilters = useCallback(
    (opts: {
      categories?: string[];
      searchTerm?: string;
      sortBy?: string;
      wristFilter?: string;
      page?: number;
    }) => {
      const cats = opts.categories ?? selectedCategories;
      const qVal = opts.searchTerm ?? searchTerm;
      const sortVal = opts.sortBy ?? sortBy;
      const wristVal = normalizeWristSize(opts.wristFilter ?? wristFilter);
      const pageVal = opts.page ?? page;

      const params = new URLSearchParams();
      if (cats.length) params.set("categories", cats.join(","));
      if (qVal) params.set("q", qVal);
      if (sortVal) params.set("sort", sortVal);
      if (wristVal) params.set("wrist", wristVal);
      if (pageVal > 1) params.set("page", String(pageVal));

      router.push(`/shop?${params.toString()}`, { scroll: false });
    },
    [selectedCategories, searchTerm, sortBy, wristFilter, page, router]
  );

  const toggleCat = (catKey: string) => {
    const next = selectedCategories.includes(catKey)
      ? selectedCategories.filter((c) => c !== catKey)
      : [...selectedCategories, catKey];
    applyFilters({ categories: next, page: 1 });
  };

  const selectAll = () => applyFilters({ categories: [], searchTerm: "", wristFilter: "", page: 1 });

  // Group categories
  const groupedCategories = useMemo(() => {
    return categories.reduce((acc, cat) => {
      const grp = cat.group || "Ostatní";
      if (!acc[grp]) acc[grp] = [];
      acc[grp].push(cat);
      return acc;
    }, {} as Record<string, Category[]>);
  }, [categories]);

  // Get all wrist sizes from variants
  const allWristSizes = useMemo(() => {
    const sizes: string[] = [];
    products.forEach((p) => {
      const direct = normalizeWristSize(p.wrist_size);
      if (direct) sizes.push(direct);
      (p.variants || []).forEach((v) => {
        const val = normalizeWristSize(v.wrist_size);
        if (val) sizes.push(val);
      });
    });
    return Array.from(new Set(sizes.filter(Boolean))).sort(compareWristSizes);
  }, [products]);

  // Filter products
  const filteredProducts = useMemo(() => {
    const normalizedWristFilter = normalizeWristSize(wristFilter);
    return products.filter((p) => {
      const isActive = p.active !== false;
      const inStock = Number(p.stock ?? 0) > 0;
      if (!isActive || !inStock) return false;
      const catKey = p.category_key || "";
      const catSlug = catKey.split("-")[0] || "";
      const matchesCat =
        !selectedCategories.length ||
        selectedCategories.includes(catKey) ||
        selectedCategories.includes(catSlug) ||
        selectedCategories.some((sel) => catKey.includes(sel) || catSlug === sel);
      const matchesText = (p.name || "").toLowerCase().includes(searchTerm.toLowerCase());
      const matchesWrist =
        !normalizedWristFilter ||
        normalizeWristSize(p.wrist_size) === normalizedWristFilter ||
        (Array.isArray(p.variants) &&
          p.variants.some(
            (v) => normalizeWristSize(v.wrist_size) === normalizedWristFilter
          ));
      return matchesCat && matchesText && matchesWrist;
    });
  }, [products, selectedCategories, searchTerm, wristFilter]);

  // Sort products
  const sortedProducts = useMemo(() => {
    const list = [...filteredProducts];
    switch (sortBy) {
      case "price_asc":
        return list.sort((a, b) => (Number(a.price) || 0) - (Number(b.price) || 0));
      case "price_desc":
        return list.sort((a, b) => (Number(b.price) || 0) - (Number(a.price) || 0));
      case "name_asc":
        return list.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
      case "name_desc":
        return list.sort((a, b) => String(b.name || "").localeCompare(String(a.name || "")));
      default:
        return list;
    }
  }, [filteredProducts, sortBy]);

  // Pagination
  const total = sortedProducts.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;
  const pageItems = sortedProducts.slice(start, start + PAGE_SIZE);
  const shownFrom = total === 0 ? 0 : start + 1;
  const shownTo = Math.min(start + PAGE_SIZE, total);

  useEffect(() => {
    if (page > totalPages && totalPages > 0) {
      applyFilters({ page: totalPages });
    }
  }, [page, totalPages, applyFilters]);

  return (
    <section
      id="shop-root"
      className="pt-24 sm:pt-28 pb-12 bg-gradient-to-br from-beige-800 via-beige-600 to-beige-400 min-h-screen text-white overflow-x-hidden"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 md:px-8">
        <div className="relative text-center mb-8 sm:mb-10">
          <span
            className="absolute left-1/2 top-1/2 h-20 w-64 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-r from-amber-200/50 via-white/40 to-amber-300/50 blur-3xl"
            aria-hidden="true"
          />
          <h2 className="relative inline-block font-['Great_Vibes'] text-[clamp(2.5rem,6vw,4.5rem)] text-transparent bg-clip-text bg-gradient-to-r from-amber-100 via-white to-amber-300 drop-shadow-[0_6px_18px_rgba(0,0,0,0.45)] animate-float animate-gradient-x">
            E-shop
          </h2>
        </div>

        <div className="flex flex-col md:flex-row gap-8 items-start">
          {/* Sidebar */}
          <aside className="w-full md:w-1/4 bg-white/10 backdrop-blur-sm p-4 sm:p-5 rounded-2xl shadow-lg min-w-0">
            <h3 className="text-lg font-semibold mb-4">Kategorie</h3>
            <input
              type="text"
              placeholder="Hledat produkt..."
              className="w-full mb-4 px-3 py-2 border rounded text-black"
              value={searchTerm}
              onChange={(e) => applyFilters({ searchTerm: e.target.value, page: 1 })}
            />
            <ul className="space-y-4 text-sm">
              {Object.entries(groupedCategories).map(([groupName, cats]) => (
                <li key={groupName}>
                  <div className="flex justify-between items-center">
                    <strong>{groupName.toUpperCase()}</strong>
                    <button
                      onClick={() => {
                        const allKeys = cats.map((c) => `${c.slug}-${c.id}`);
                        const allSelected = cats.every((c) =>
                          selectedCategories.includes(`${c.slug}-${c.id}`)
                        );
                        const next = allSelected
                          ? selectedCategories.filter((c) => !allKeys.includes(c))
                          : Array.from(new Set([...selectedCategories, ...allKeys]));
                        applyFilters({ categories: next, page: 1 });
                      }}
                      className="text-sm text-beige-200 hover:underline"
                    >
                      {cats.every((c) => selectedCategories.includes(`${c.slug}-${c.id}`))
                        ? "Odebrat"
                        : "Vybrat"}
                    </button>
                  </div>
                  <ul className="ml-4 mt-1 space-y-1">
                    {cats.map((cat) => {
                      const key = `${cat.slug}-${cat.id}`;
                      return (
                        <li key={cat.id}>
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={selectedCategories.includes(key)}
                              onChange={() => toggleCat(key)}
                            />
                            <span>{cat.name}</span>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </li>
              ))}
            </ul>
            <div className="mt-6 space-y-2">
              <button
                onClick={selectAll}
                className="w-full bg-beige-600 text-white py-2 rounded"
              >
                Zobrazit vše
              </button>
              {allWristSizes.length > 0 && (
                <div className="pt-2 space-y-1">
                  <label className="block text-sm font-semibold">Obvod</label>
                  <select
                    value={wristFilter}
                    onChange={(e) => applyFilters({ wristFilter: e.target.value, page: 1 })}
                    className="w-full px-3 py-2 border rounded text-black"
                  >
                    <option value="">Všechny obvody</option>
                    {allWristSizes.map((w) => (
                      <option key={w} value={w}>
                        {formatWristSize(w)}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="pt-2 space-y-1">
                <label className="block text-sm font-semibold">Řazení</label>
                <select
                  value={sortBy}
                  onChange={(e) => applyFilters({ sortBy: e.target.value, page: 1 })}
                  className="w-full px-3 py-2 border rounded text-black"
                >
                  <option value="">Dle výchozího</option>
                  <option value="price_asc">Cena: od nejnižší</option>
                  <option value="price_desc">Cena: od nejvyšší</option>
                  <option value="name_asc">Název: A → Z</option>
                  <option value="name_desc">Název: Z → A</option>
                </select>
              </div>
            </div>
          </aside>

          {/* Products */}
          <main className="flex-1">
            {loading ? (
              <div className="text-center text-beige-200">Načítám produkty...</div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                  {pageItems.map((product) => {
                    const inStock = Number(product.stock ?? 0) > 0;
                    const badgeClass = !inStock
                      ? "bg-gradient-to-r from-beige-600 to-beige-700 text-white"
                      : product.stock! <= 5
                      ? "bg-gradient-to-r from-amber-400 to-amber-600 text-black animate-pulse"
                      : "bg-gradient-to-r from-emerald-400 to-green-600 text-white";
                    const primaryWristSize = getPrimaryWristSize(product);
                    const title = emojify(product.name);
                    const wristDisplay = formatWristSize(primaryWristSize) || null;
                    const descriptionPreview = buildDescriptionPreview(product.description);

                    return (
                      <div
                        key={product.id}
                        className="rounded-2xl p-[1px] bg-gradient-to-br from-zinc-200/70 via-amber-100/30 to-yellow-400/60 shadow-[0_18px_35px_-22px_rgba(0,0,0,0.85)]"
                      >
                        <div className="bg-gradient-to-b from-white/20 via-white/8 to-white/12 backdrop-blur-sm rounded-2xl overflow-hidden flex flex-col border border-white/20">
                        {product.image ? (
                          <img
                            src={product.image}
                            alt={product.name}
                            className="w-full h-48 object-cover ring-1 ring-white/30"
                          />
                        ) : (
                          <div className="w-full h-48 bg-white/5" />
                        )}
                        <div className="p-4 flex flex-col flex-grow">
                          <div className="flex items-start justify-between gap-2">
                            <Link
                              href={`/products/${slugify(product.name)}`}
                              className="text-lg font-semibold mb-2 hover:underline text-white block flex-1 product-title-clamp leading-7 min-h-[3.5rem] max-h-[3.5rem]"
                            >
                              {title}
                            </Link>
                            <span
                              className={`text-[11px] px-2.5 py-1 rounded-full whitespace-nowrap ${badgeClass}`}
                              title={inStock ? `Skladem: ${product.stock}` : "Vyprodáno"}
                            >
                              {inStock ? `Skladem: ${product.stock}` : "Vyprodáno"}
                            </span>
                          </div>
                          <div className="mb-2 text-sm font-semibold text-beige-200 min-h-[1.25rem]">
                            {wristDisplay ? (
                              <>Obvod: {wristDisplay}</>
                            ) : (
                              <span className="opacity-0">Obvod: 0 cm</span>
                            )}
                          </div>
                          <p className="text-beige-200 mb-4">
                            {(Number(product.price) || 0).toFixed(2)} Kč
                          </p>
                          <div className="mt-auto">
                            <p className="text-[13px] leading-5 text-beige-100/90 mb-3 product-desc-clamp h-[2.5rem]">
                              {descriptionPreview}
                            </p>
                            <button
                              onClick={() =>
                                inStock &&
                                addToCart({
                                  id: product.id,
                                  name: product.name,
                                  price: Number(product.price) || 0,
                                  image: product.image,
                                  stock: product.stock ?? undefined,
                                })
                              }
                              disabled={!inStock}
                              className={`w-full text-center text-white py-2 rounded-lg transition ${
                                inStock
                                  ? "bg-beige-600 hover:bg-beige-700"
                                  : "bg-gray-300 cursor-not-allowed"
                              }`}
                            >
                              {inStock ? "Přidat do košíku" : "Vyprodáno"}
                            </button>
                          </div>
                        </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {filteredProducts.length === 0 && !loading && (
                  <div className="text-center text-beige-200 font-medium mt-6">
                    Nenalezeny žádné produkty pro vybrané filtry.
                  </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="mt-10">
                    <div className="flex flex-col items-center gap-3">
                      <div className="text-sm text-beige-100/90">
                        Zobrazeno <span className="font-semibold">{shownFrom}</span> –{" "}
                        <span className="font-semibold">{shownTo}</span> z{" "}
                        <span className="font-semibold">{total}</span>
                      </div>
                      <div className="flex items-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full px-2 py-1 shadow-lg">
                        <button
                          disabled={page === 1}
                          onClick={() => applyFilters({ page: 1 })}
                          className="px-3 py-2 rounded-full hover:bg-white/15 disabled:opacity-40 transition"
                        >
                          «
                        </button>
                        <button
                          disabled={page === 1}
                          onClick={() => applyFilters({ page: Math.max(1, page - 1) })}
                          className="px-3 py-2 rounded-full hover:bg-white/15 disabled:opacity-40 transition"
                        >
                          ‹
                        </button>
                        {getPageList(page, totalPages).map((n, idx) =>
                          n === "…" ? (
                            <span key={`dots-${idx}`} className="px-2 text-beige-100/70">
                              …
                            </span>
                          ) : (
                            <button
                              key={n}
                              onClick={() => applyFilters({ page: n as number })}
                              className={`px-3 py-2 rounded-full transition ${
                                n === page
                                  ? "bg-beige-600 text-white shadow-md"
                                  : "hover:bg-white/15"
                              }`}
                            >
                              {n}
                            </button>
                          )
                        )}
                        <button
                          disabled={page === totalPages}
                          onClick={() => applyFilters({ page: Math.min(totalPages, page + 1) })}
                          className="px-3 py-2 rounded-full hover:bg-white/15 disabled:opacity-40 transition"
                        >
                          ›
                        </button>
                        <button
                          disabled={page === totalPages}
                          onClick={() => applyFilters({ page: totalPages })}
                          className="px-3 py-2 rounded-full hover:bg-white/15 disabled:opacity-40 transition"
                        >
                          »
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>
    </section>
  );
}

export default function ShopPage() {
  return (
    <Suspense fallback={
      <section className="pt-24 pb-12 min-h-screen bg-gradient-to-br from-beige-800 via-beige-600 to-beige-400 flex items-center justify-center text-white">
        Načítám e-shop...
      </section>
    }>
      <ShopPageContent />
    </Suspense>
  );
}
