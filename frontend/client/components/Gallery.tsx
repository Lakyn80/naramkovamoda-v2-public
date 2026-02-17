"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { fetchProducts } from "../lib/api";
import { slugify } from "../lib/slugify";
import { emojify } from "../lib/emojify";
import { resolveMediaUrl } from "../lib/media";
import type { Product } from "../lib/types";

export default function Gallery() {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    fetchProducts()
      .then((data) => setProducts(Array.isArray(data) ? data.slice(0, 8) : []))
      .catch((e) => console.error("Chyba při načítání produktů:", e));
  }, []);

  if (products.length === 0) {
    return (
      <section id="galerie" className="py-16 sm:py-20 px-4 sm:px-6 md:px-8 bg-gradient-to-b from-beige-100 to-beige-200">
        <h2 className="text-4xl sm:text-5xl font-extrabold text-center mb-10 bg-gradient-to-r from-beige-600 via-beige-400 to-beige-500 text-transparent bg-clip-text">
          Galerie
        </h2>
        <p className="text-center text-beige-700">Načítám produkty...</p>
      </section>
    );
  }

  return (
    <section
      id="galerie"
      className="relative py-16 sm:py-20 px-4 sm:px-6 md:px-8 bg-gradient-to-b from-beige-100 to-beige-200 overflow-hidden"
    >
      <h2 className="text-4xl sm:text-5xl font-extrabold text-center mb-10 bg-gradient-to-r from-beige-600 via-beige-400 to-beige-500 text-transparent bg-clip-text drop-shadow-sm">
        Galerie
      </h2>

      <div className="max-w-6xl mx-auto grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6">
        {products.map((product) => {
          const imageUrl = resolveMediaUrl(product.image_thumb_url || product.image_url);
          const productSlug = slugify(product.name);
          return (
            <Link
              key={product.id}
              href={`/products/${productSlug}`}
              className="group"
            >
              <div className="bg-white/60 backdrop-blur-sm rounded-2xl overflow-hidden shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-1">
                <div className="aspect-square overflow-hidden">
                  {imageUrl ? (
                    <img
                      src={imageUrl}
                      alt={product.name}
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="w-full h-full bg-beige-100 flex items-center justify-center text-beige-400 text-sm">
                      Bez obrázku
                    </div>
                  )}
                </div>
                <div className="px-3 py-3">
                  <p className="text-center text-beige-900 font-semibold text-sm sm:text-base line-clamp-2 leading-snug min-h-[2.75rem]">
                    {emojify(product.name)}
                  </p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="text-center mt-10">
        <Link
          href="/shop"
          className="inline-block px-8 py-3 bg-beige-600 hover:bg-beige-700 text-white font-semibold rounded-full shadow-lg transition duration-300"
        >
          Zobrazit vše
        </Link>
      </div>
    </section>
  );
}
