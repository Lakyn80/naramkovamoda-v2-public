"use client";

import React, { useMemo, useState } from "react";

function normalizePhone(input: string): string {
  return (input || "").replace(/[^\d]/g, "");
}

interface WhatsAppWidgetProps {
  phone?: string;
  defaultMessage?: string;
  quickReplies?: string[];
  position?: "left" | "right";
  label?: string;
}

export default function WhatsAppWidget({
  phone = "+420 776 47 97 47",
  defaultMessage = "Dobrý den, rád/a bych se zeptal/a na dostupnost.",
  quickReplies = [
    "Dobrý den, máte tento náramek skladem?",
    "Jaké jsou možnosti a ceny dopravy?",
    "Šla by udělat personalizace (jméno/délka)?",
  ],
  position = "right",
  label = "Jsme na WhatsAppu",
}: WhatsAppWidgetProps) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState(defaultMessage);

  const normPhone = useMemo(() => normalizePhone(phone), [phone]);

  const waHref = useMemo(() => {
    const encoded = encodeURIComponent(msg || "");
    return `https://api.whatsapp.com/send?phone=${normPhone}&text=${encoded}`;
  }, [normPhone, msg]);

  const sideClasses = position === "left" ? "left-3 sm:left-4 md:left-8" : "right-3 sm:right-4 md:right-8";

  const WhatsIcon = (
    <svg viewBox="0 0 32 32" className="w-6 h-6" aria-hidden="true">
      <path
        d="M19.11 17.36c-.3-.15-1.76-.86-2.03-.96-.27-.1-.47-.15-.68.15-.2.3-.78.96-.95 1.16-.17.2-.35.22-.65.07-.3-.15-1.28-.47-2.44-1.5-.9-.8-1.51-1.78-1.69-2.08-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.68-1.63-.93-2.24-.25-.6-.5-.5-.68-.5-.17 0-.37-.02-.57-.02-.2 0-.52.07-.8.37-.27.3-1.05 1.02-1.05 2.49 0 1.47 1.07 2.9 1.22 3.1.15.2 2.11 3.22 5.11 4.52.71.31 1.26.5 1.69.64.71.23 1.36.2 1.87.12.57-.08 1.76-.72 2.01-1.42.25-.7.25-1.3.17-1.42-.07-.12-.27-.2-.57-.35z"
        fill="currentColor"
      />
      <path
        d="M26.69 5.31C23.86 2.5 20.08 1 16 1S8.14 2.5 5.31 5.31C2.5 8.14 1 11.92 1 16c0 2.61.78 5.14 2.25 7.3L1.83 30l6.83-1.8C10.86 29.42 13.38 30 16 30c4.08 0 7.86-1.5 10.69-4.31C29.5 22.86 31 19.08 31 15s-1.5-7.86-4.31-10.69zM16 27.33c-2.45 0-4.81-.69-6.86-1.98l-.49-.3-4.05 1.07 1.08-3.95-.32-.5A11.28 11.28 0 0 1 4.67 16c0-6.26 5.07-11.33 11.33-11.33S27.33 9.74 27.33 16 22.26 27.33 16 27.33z"
        fill="currentColor"
      />
    </svg>
  );

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`fixed bottom-4 sm:bottom-6 md:bottom-8 ${sideClasses} z-50 group
          rounded-full p-3 sm:p-4 md:p-5 shadow-xl
          bg-gradient-to-br from-beige-800 via-beige-600 to-beige-400
          text-white transition-transform hover:scale-105`}
        aria-label="Otevřít WhatsApp chat"
      >
        <span className="flex items-center justify-center">{WhatsIcon}</span>
        <span
          className="absolute -top-2 -right-2 h-3 w-3 rounded-full bg-white/90 shadow
                     group-hover:animate-ping"
          aria-hidden="true"
        />
      </button>

      {/* Panel */}
      {open && (
        <div
          className={`fixed bottom-20 sm:bottom-24 md:bottom-28 ${sideClasses} z-50
                      w-[calc(100vw-1.5rem)] sm:w-[90vw] max-w-[360px]`}
        >
          <div className="rounded-2xl overflow-hidden shadow-2xl backdrop-blur-xl bg-white/60 border border-white/40">
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-beige-800/90 via-beige-600/80 to-beige-400/70">
              <div className="h-9 w-9 rounded-full flex items-center justify-center bg-white/20 text-white">
                {WhatsIcon}
              </div>
              <div className="flex-1">
                <div className="text-white font-semibold leading-tight">{label}</div>
                <div className="text-[12px] text-white/80">Odpovíme co nejdříve ✨</div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-white/80 hover:text-white text-xl"
                aria-label="Zavřít"
              >
                ×
              </button>
            </div>

            {/* Body */}
            <div className="px-4 pt-3 pb-4 text-slate-900">
              {quickReplies?.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {quickReplies.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => setMsg(q)}
                      className="text-xs md:text-[13px] px-3 py-1.5 rounded-full
                                 bg-white/70 hover:bg-white/80 border border-white/60
                                 transition text-slate-900"
                      type="button"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm text-slate-800">Vaše zpráva</label>
                <textarea
                  value={msg}
                  onChange={(e) => setMsg(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl bg-white/80 text-slate-900 placeholder-slate-500
                             border border-white/70 focus:outline-none focus:ring-2
                             focus:ring-beige-300/70 p-3"
                  placeholder="Napište svůj dotaz…"
                />
              </div>

              <div className="mt-3 flex items-center justify-between gap-3">
                <a
                  href={waHref}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 inline-flex items-center justify-center gap-2
                             rounded-xl px-4 py-2.5 font-medium text-white
                             bg-gradient-to-r from-beige-600 to-beige-400
                             hover:opacity-95 transition shadow"
                >
                  Odeslat na WhatsApp
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
