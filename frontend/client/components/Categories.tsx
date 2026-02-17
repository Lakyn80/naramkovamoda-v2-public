"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchCategories } from "../lib/api";
import { slugify } from "../lib/slugify";
import type { Category } from "../lib/types";

export default function Categories() {
  const router = useRouter();
  const [categories, setCategories] = useState<{ label: string; slug: string }[]>([]);

  useEffect(() => {
    fetchCategories()
      .then((data) => {
        const mapped = (data || [])
          .map((cat: Category) => {
            const label = cat?.name || "";
            const slug = cat?.slug || slugify(label);
            return label ? { label, slug } : null;
          })
          .filter((x): x is { label: string; slug: string } => x !== null);
        setCategories(mapped);
      })
      .catch((err) => {
        console.error("Chyba načtení kategorií:", err);
        setCategories([]);
      });
  }, []);

  const handleClick = (slug: string) => {
    router.push(`/shop?categories=${encodeURIComponent(slug)}`);
  };

  const marqueeList = categories.length ? [...categories, ...categories] : [];

  return (
    <section
      id="kategorie"
      className="relative py-16 sm:py-20 px-4 sm:px-6 md:px-8 bg-gradient-to-b from-beige-200 to-beige-100 overflow-hidden"
    >
      <div className="backdrop-blur-sm bg-white/10 rounded-2xl shadow-2xl max-w-5xl mx-auto p-6 sm:p-10 relative z-10">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-6 sm:mb-8 text-beige-900 drop-shadow-sm">
          Kategorie
        </h2>

        {marqueeList.length ? (
          <div className="overflow-hidden relative">
            <div className="flex gap-3 sm:gap-6 animate-scroll whitespace-nowrap">
              {marqueeList.map((cat, index) => (
                <button
                  key={`${cat.slug}-${index}`}
                  onClick={() => handleClick(cat.slug)}
                  className="bg-beige-500/20 hover:bg-beige-100 text-beige-900 shadow-md backdrop-blur-sm rounded-full px-4 sm:px-6 py-2 sm:py-3 text-sm font-medium transition-all duration-300 whitespace-nowrap"
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-center text-beige-700/80">Načítám kategorie…</p>
        )}
      </div>

      <style jsx>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        .animate-scroll {
          animation: scroll 30s linear infinite;
        }
        .animate-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
    </section>
  );
}
