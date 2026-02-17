"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "../../context/CartContext";
import { buildApiUrl } from "../../lib/api";

const SHIPPING_FEE_CZK = Number(process.env.NEXT_PUBLIC_SHIPPING_FEE_CZK ?? 89);

function toMoney(n: number): number {
  const cents = Math.round(Number(n) * 100);
  return cents / 100;
}

export default function CheckoutPage() {
  const { cartItems, clearCart, shippingMode } = useCart();
  const router = useRouter();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    address: "",
    note: "",
  });
  const [phase, setPhase] = useState<"form" | "qr" | "submitted">("form");
  const [vs, setVs] = useState<number | null>(null);
  const [qrError, setQrError] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const subtotal = useMemo(() => {
    return cartItems.reduce((sum, item) => {
      const q = Number(item.quantity) || 0;
      const p = Number(item.price) || 0;
      return sum + q * p;
    }, 0);
  }, [cartItems]);

  const total = useMemo(() => {
    const shipping = shippingMode === "pickup" ? 0 : SHIPPING_FEE_CZK;
    return toMoney(subtotal + shipping);
  }, [subtotal, shippingMode]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleShowQr = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cartItems.length) return;
    const newVs = Math.floor(100000 + Math.random() * 900000);
    setVs(newVs);
    setPhase("qr");
  };

  // Generate QR code – payload z backendu (MERCHANT_IBAN z ENV), platný SPD 1.0 formát
  useEffect(() => {
    if (phase !== "qr" || !vs || total <= 0) return;

    (async () => {
      setQrError("");
      try {
        const url = buildApiUrl(
          `/api/payments/qr/payload?amount=${encodeURIComponent(toMoney(total).toFixed(2))}&vs=${vs}&msg=${encodeURIComponent(`Objednavka ${vs}`)}`
        );
        const res = await fetch(url);
        const data = (await res.json()) as { ok?: boolean; payload?: string; error?: string };
        if (!res.ok || !data?.payload) {
          throw new Error(data?.error || "Nepodařilo se získat platební údaje. Zkontrolujte MERCHANT_IBAN na serveru.");
        }
        const QRCode = (await import("qrcode")).default;
        const dataUrl = await QRCode.toDataURL(data.payload, { width: 256, margin: 1 });
        setQrDataUrl(dataUrl);
      } catch (e) {
        setQrError(String((e as Error)?.message || e));
      }
    })();
  }, [phase, total, vs]);

  const handleConfirmPaidAndSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);

    try {
      // Integrační scénář: QR payload z /api/payments/qr/payload + POST /api/orders
      // musí vytvořit objednávku, poslat potvrzení zákazníkovi i adminovi a vyčistit košík.
      const orderData = {
        name: formData.name,
        email: formData.email,
        address: formData.address,
        note: formData.note,
        vs: vs !== null && vs !== undefined ? String(vs) : "",
        totalCzk: total,
        shippingCzk: shippingMode === "pickup" ? 0 : SHIPPING_FEE_CZK,
        shippingMode,
        items: cartItems.map((item) => ({
          id: item.id,
          variantId: item.variantId,
          name: item.variantName
            ? `${item.name} (${item.variantName}${item.wristSize ? ` / ${item.wristSize}` : ""})`
            : item.name,
          quantity: Number(item.quantity) || 0,
          price: Number(item.price) || 0,
        })),
      };

      const response = await fetch(buildApiUrl("/api/orders"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(orderData),
      });

      if (response.ok) {
        clearCart();
        setPhase("submitted");
      } else {
        let msg = "Nepodařilo se odeslat objednávku. Zkuste to prosím znovu.";
        try {
          const data = await response.json();
          msg = data?.error || data?.message || msg;
        } catch {
          // ignore
        }
        console.error("Chyba při odesílání objednávky");
        alert(msg);
      }
    } catch (error) {
      console.error("Fetch error:", error);
      alert("Došlo k chybě při odesílání. Zkuste to prosím znovu.");
    } finally {
      setSubmitting(false);
    }
  };

  if (phase === "submitted") {
    return (
      <section className="pt-24 sm:pt-28 pb-12 px-4 sm:px-6 md:px-8 min-h-screen text-center text-beige-900 bg-gradient-to-br from-beige-300 via-white to-beige-200 overflow-x-hidden">
        <h2 className="text-2xl sm:text-3xl font-bold mb-4">
          Děkujeme za objednávku!
        </h2>
        <p className="mb-6">
          Brzy se vám ozveme s potvrzením a detaily doručení.
        </p>
        <button
          onClick={() => router.push("/")}
          className="bg-beige-600 hover:bg-beige-700 text-white py-2 px-6 rounded-lg text-lg transition"
        >
          Zpět na hlavní stránku
        </button>
      </section>
    );
  }

  if (phase === "qr") {
    return (
      <section className="pt-24 sm:pt-28 pb-12 px-4 sm:px-6 md:px-8 min-h-screen text-beige-900 bg-gradient-to-br from-beige-300 via-white to-beige-200 overflow-x-hidden">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4 text-center">
            Platba objednávky
          </h2>
          <p className="text-center text-beige-800 mb-6">
            Naskenujte QR kód ve své bankovní aplikaci. <br />
            Částka: <b>{toMoney(total).toFixed(2)} CZK</b>
          </p>
          <div className="text-center text-sm text-beige-800 mb-4">
            <div>VS: <b>{vs ?? "-"}</b></div>
            <div>Číslo účtu: <b>360781605/0300</b></div>
          </div>

          <div className="flex flex-col items-center gap-4 bg-white rounded-2xl shadow p-6">
            {qrError ? (
              <div className="text-red-600">{qrError}</div>
            ) : qrDataUrl ? (
              <img
                src={qrDataUrl}
                alt="QR platba"
                className="border rounded-lg shadow w-64 h-64"
              />
            ) : (
              <div className="text-gray-500">Generuji QR kód...</div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setPhase("form")}
                className="px-4 py-2 rounded-md border"
              >
                Zpět
              </button>
              <button
                onClick={handleConfirmPaidAndSubmit}
                disabled={submitting}
                className="bg-beige-600 hover:bg-beige-700 text-white font-semibold py-2 px-4 rounded-md transition disabled:opacity-60"
              >
                {submitting ? "Odesílám..." : "Potvrzuji platbu, odeslat objednávku"}
              </button>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="pt-24 sm:pt-28 pb-12 px-4 sm:px-6 md:px-8 min-h-screen text-beige-900 bg-gradient-to-br from-beige-300 via-white to-beige-200 overflow-x-hidden">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold mb-8 text-center">
          Pokladna
        </h2>
        {cartItems.length === 0 ? (
          <p className="text-center text-beige-600">Košík je prázdný.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <form onSubmit={handleShowQr} className="space-y-4">
              <input
                type="text"
                name="name"
                placeholder="Jméno a příjmení"
                required
                className="w-full border px-4 py-2 rounded-md"
                value={formData.name}
                onChange={handleChange}
              />
              <input
                type="email"
                name="email"
                placeholder="Email"
                required
                className="w-full border px-4 py-2 rounded-md"
                value={formData.email}
                onChange={handleChange}
              />
              <textarea
                name="address"
                placeholder="Adresa"
                required
                className="w-full border px-4 py-2 rounded-md"
                value={formData.address}
                onChange={handleChange}
              />
              <textarea
                name="note"
                placeholder="Poznámka (volitelné)"
                className="w-full border px-4 py-2 rounded-md"
                value={formData.note}
                onChange={handleChange}
              />
              <button
                type="submit"
                className="bg-beige-600 hover:bg-beige-700 text-white font-semibold py-2 px-6 rounded-md transition w-full sm:w-auto"
              >
                Zaplatit QR
              </button>
              <button
                type="button"
                onClick={() => router.back()}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-white/70 border border-beige-200 text-beige-700 px-4 py-2 font-semibold shadow-sm hover:bg-white transition w-full sm:w-auto mt-3 sm:mt-0 sm:ml-3"
              >
                ⬅︎ Zpět do košíku
              </button>
            </form>

            <div>
              <h3 className="text-xl font-semibold mb-4">Vaše objednávka:</h3>
              <ul className="space-y-2 text-beige-800 text-sm">
                {cartItems.map((item) => {
                  const lineName = item.variantName
                    ? `${item.name} (${item.variantName}${item.wristSize ? ` / ${item.wristSize}` : ""})`
                    : item.name;
                  const key = item.lineKey || `${item.id}-${lineName}`;
                  return (
                    <li key={key} className="flex justify-between">
                      <span>
                        {item.quantity}× {lineName}
                      </span>
                      <span>
                        {toMoney(item.quantity * item.price).toFixed(2)} Kč
                      </span>
                    </li>
                  );
                })}
              </ul>
              <div className="mt-4 text-right text-sm">
                Mezisoučet: {toMoney(subtotal).toFixed(2)} Kč
              </div>
              <div className="text-right text-sm">
                Doprava:{" "}
                {shippingMode === "pickup"
                  ? "Osobní vyzvednutí (0 Kč)"
                  : `Poštou: ${toMoney(SHIPPING_FEE_CZK).toFixed(2)} Kč`}
              </div>
              <div className="mt-1 font-bold text-right text-lg">
                Celkem: {toMoney(total).toFixed(2)} Kč
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
