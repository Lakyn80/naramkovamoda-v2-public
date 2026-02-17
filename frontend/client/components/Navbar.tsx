"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCart } from "../context/CartContext";
import { ShoppingBag, ShoppingCart } from "lucide-react";

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [mounted, setMounted] = useState(false);

  const pathname = usePathname();
  const router = useRouter();
  const isLanding = pathname === "/";

  const { cartItems } = useCart();
  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  const handleHomeClick = () => {
    setMenuOpen(false);
    if (!isLanding) {
      router.push("/");
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => setMounted(true), []);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navTextClass = isLanding
    ? "text-white/95 drop-shadow-md hover:text-white"
    : scrolled
      ? "text-beige-950 font-semibold drop-shadow-sm hover:text-beige-700"
      : "text-beige-950 font-semibold drop-shadow-sm hover:text-beige-700";

  const navBgClass = isLanding
    ? "bg-white/5 backdrop-blur-md"
    : "bg-white/10 backdrop-blur-md";
  const logoSrc = "/header_mark_white.png";

  return (
    <nav
      className={`fixed top-0 left-0 right-0 w-full z-50 px-4 sm:px-6 md:px-8 py-2 ${navBgClass} transition-all duration-300 ${
        isLanding ? "border-b border-white/20" : "border-b border-beige-900/10"
      }`}
    >
      <div className="flex justify-between items-center gap-3 max-w-7xl mx-auto w-full min-w-0">
        <div
          className="flex items-center gap-2 sm:gap-3 cursor-pointer transition shrink-0 min-w-0 flex-1 sm:flex-initial"
          onClick={handleHomeClick}
        >
          <img
            src={logoSrc}
            alt=""
            width={40}
            height={40}
            className="flex-shrink-0 object-contain w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12"
            aria-hidden
          />

          <span
            className={`text-base sm:text-xl md:text-2xl tracking-wide font-['Playfair_Display'] truncate ${
              isLanding
                ? "text-white/95 drop-shadow-md hover:text-white"
                : scrolled
                  ? "font-bold text-beige-900 hover:text-beige-600"
                  : "font-bold bg-gradient-to-r from-beige-700 via-beige-400 to-beige-700 bg-clip-text text-transparent"
            }`}
          >
            Náramky pro radost
          </span>
        </div>

        <div className="sm:hidden relative flex-shrink-0">
          <button
            className={`${isLanding ? "text-white" : "text-beige-900"} text-2xl focus:outline-none relative p-1`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menu"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
            {mounted && cartCount > 0 && (
              <span
                data-cart-badge
                className={`absolute -top-2 -right-2 text-sm font-bold rounded-full min-w-[24px] h-[24px] flex items-center justify-center shadow-lg ring-2 ${
                  isLanding ? "bg-beige-700 text-white ring-white/80" : "bg-beige-600 text-white ring-white"
                }`}
              >
                {cartCount}
              </span>
            )}
          </button>
        </div>

        <ul className="hidden sm:flex items-center gap-4 md:gap-6 text-sm sm:text-base font-medium list-none">
          {!isLanding && (
            <>
              <li>
                <span
                  onClick={handleHomeClick}
                  className={`cursor-pointer ${navTextClass} transition`}
                >
                  Domů
                </span>
              </li>
            </>
          )}
          <li>
            <Link href="/shop" className={`flex items-center gap-1.5 ${navTextClass} transition`}>
              <ShoppingBag className="w-5 h-5" aria-hidden />
              E-shop
            </Link>
          </li>
          <li>
            <Link
              href="/cart"
              className={`flex items-center gap-1.5 ${navTextClass} transition relative`}
            >
              <ShoppingCart className="w-5 h-5" aria-hidden />
              {mounted && cartCount > 0 && (
                <span
                  data-cart-badge
                  className={`absolute -top-2.5 -right-2.5 text-sm font-bold rounded-full min-w-[24px] h-[24px] flex items-center justify-center shadow-lg ring-2 ${
                    isLanding ? "bg-beige-700 text-white ring-white/80" : "bg-beige-600 text-white ring-white"
                  }`}
                >
                  {cartCount}
                </span>
              )}
            </Link>
          </li>
        </ul>
      </div>

      {menuOpen && (
        <div
          className={`sm:hidden mt-3 rounded-xl shadow-xl px-5 py-4 list-none ${
            isLanding ? "bg-white/10 backdrop-blur-md text-white" : "bg-white/90 text-beige-900"
          }`}
        >
          {!isLanding && (
            <>
              <div onClick={() => setMenuOpen(false)}>
                <span onClick={handleHomeClick} className="block py-2 hover:text-beige-600 cursor-pointer">
                  Domů
                </span>
              </div>
            </>
          )}
          <Link
            href="/shop"
            onClick={() => setMenuOpen(false)}
            className="block py-2 hover:opacity-80"
          >
            E-shop
          </Link>
          <Link
            href="/cart"
            onClick={() => setMenuOpen(false)}
            className="block py-2 hover:opacity-80"
          >
            Košík {cartCount > 0 && `(${cartCount})`}
          </Link>
        </div>
      )}
    </nav>
  );
}
