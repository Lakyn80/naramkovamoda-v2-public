"use client";

import React from "react";
import Link from "next/link";
import { useCart } from "../../context/CartContext";
import { absoluteUploadUrl } from "../../lib/media";
import { emojify } from "../../lib/emojify";

const SHIPPING_FEE_CZK = Number(process.env.NEXT_PUBLIC_SHIPPING_FEE_CZK ?? 89);

function toMoney(n: number): number {
  const cents = Math.round(Number(n) * 100);
  return cents / 100;
}

export default function CartPage() {
  const {
    cartItems,
    removeFromCart,
    increaseQuantity,
    decreaseQuantity,
    shippingMode,
    setShippingMode,
  } = useCart();

  const subtotal = cartItems.reduce((sum, item) => {
    const q = Number(item.quantity) || 0;
    const p = Number(item.price) || 0;
    return sum + q * p;
  }, 0);

  const shippingFee = shippingMode === "pickup" ? 0 : SHIPPING_FEE_CZK;
  const grandTotal = toMoney(subtotal + shippingFee);

  return (
    <section className="pt-24 sm:pt-28 pb-12 px-4 sm:px-6 md:px-8 min-h-screen bg-gradient-to-br from-beige-300 via-white via-30% to-beige-200 text-beige-900 overflow-x-hidden">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold mb-6 sm:mb-8 text-center">Košík</h2>

        {cartItems.length === 0 ? (
          <p className="text-center text-beige-600">Košík je prázdný.</p>
        ) : (
          <>
            <ul className="space-y-6">
              {cartItems.map((item) => {
                const imageUrl = absoluteUploadUrl(item.image);
                const max =
                  typeof item.stock === "number" && Number.isFinite(item.stock)
                    ? item.stock
                    : undefined;
                const atMax = typeof max === "number" ? item.quantity >= max : false;
                const key = item.lineKey || String(item.id) || item.name;

                return (
                  <li
                    key={key}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-2"
                  >
                    <img
                      src={imageUrl || "/placeholder.png"}
                      alt={item.name}
                      className="w-full sm:w-20 sm:h-20 h-auto object-cover rounded-lg"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "/placeholder.png";
                      }}
                    />
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg text-gray-900">
                        {emojify(item.name)}
                      </h3>
                      {(item.variantName || item.wristSize) && (
                        <div className="text-sm text-gray-700">
                          {item.variantName && <span>Varianta: {item.variantName}</span>}
                          {item.wristSize && (
                            <span className="ml-1 text-gray-600">({item.wristSize})</span>
                          )}
                        </div>
                      )}
                      <div className="flex items-center gap-2 text-sm text-gray-800 mt-2 flex-wrap">
                        <button
                          onClick={() => decreaseQuantity(item)}
                          className="px-2 py-1 bg-beige-100 hover:bg-beige-200 rounded"
                        >
                          -
                        </button>
                        <span>{item.quantity}</span>
                        <button
                          onClick={() => !atMax && increaseQuantity(item)}
                          disabled={atMax}
                          className={`px-2 py-1 rounded ${
                            atMax
                              ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                              : "bg-beige-100 hover:bg-beige-200"
                          }`}
                          title={atMax ? "Nelze přidat víc kusů, než je skladem." : ""}
                        >
                          +
                        </button>
                        <span>× {toMoney(item.price).toFixed(2)} Kč</span>
                        {typeof max === "number" && (
                          <span className="ml-2 text-xs px-2 py-0.5 rounded bg-beige-100 text-beige-800">
                            Skladem: {max}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => removeFromCart(item)}
                      className="text-sm text-red-600 hover:underline self-start sm:self-auto"
                    >
                      Odebrat
                    </button>
                  </li>
                );
              })}
            </ul>

            <div className="mt-6 flex flex-col items-end gap-2 text-base">
              <div className="w-full sm:w-auto text-right">
                Mezisoučet: {toMoney(subtotal).toFixed(2)} Kč
              </div>
              <div className="w-full sm:w-auto flex flex-col gap-2 text-sm text-beige-800 items-start sm:items-end">
                <span className="font-semibold text-base">Způsob doručení</span>
                <label className="inline-flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="shipping"
                    value="pickup"
                    checked={shippingMode === "pickup"}
                    onChange={() => setShippingMode("pickup")}
                    className="h-4 w-4 rounded-full border-2 border-beige-500 text-beige-600 focus:ring-beige-400"
                  />
                  <span>Osobní vyzvednutí (0 Kč)</span>
                </label>
                <label className="inline-flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="shipping"
                    value="post"
                    checked={shippingMode === "post"}
                    onChange={() => setShippingMode("post")}
                    className="h-4 w-4 rounded-full border-2 border-beige-500 text-beige-600 focus:ring-beige-400"
                  />
                  <span>Poštovné (Zásilkovna) +{toMoney(SHIPPING_FEE_CZK).toFixed(2)} Kč</span>
                </label>
              </div>
              <div className="w-full sm:w-auto text-right">
                Doprava:{" "}
                {shippingMode === "pickup"
                  ? "Osobní vyzvednutí (0 Kč)"
                  : `Poštou ${toMoney(shippingFee).toFixed(2)} Kč`}
              </div>
              <div className="w-full sm:w-auto text-right text-xl font-bold">
                Celkem k úhradě: {toMoney(grandTotal).toFixed(2)} Kč
              </div>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <Link
                href="/shop"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-white/70 border border-beige-200 text-beige-700 px-4 py-2 font-semibold shadow-sm hover:bg-white transition"
              >
                ⬅︎ Zpět do obchodu
              </Link>
              <Link
                href="/checkout"
                className="bg-beige-600 hover:bg-beige-700 text-white font-semibold py-2 px-6 rounded-md transition inline-block text-center"
              >
                Přejít k pokladně
              </Link>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
