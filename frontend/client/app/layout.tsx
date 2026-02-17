import "./globals.css";
import type { Metadata } from "next";
import { CartProvider } from "../context/CartContext";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import WhatsAppWidget from "../components/WhatsAppWidget";
import ServiceWorkerCleanup from "../components/ServiceWorkerCleanup";

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: {
    default: "Náramková Moda",
    template: "%s | Náramková Moda",
  },
  description: "Ozdobte se jedinečností - ručně vyráběné náramky",
  openGraph: {
    title: "Náramková Moda",
    description: "Ozdobte se jedinečností - ručně vyráběné náramky",
    type: "website",
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/header_mark_white.png", sizes: "any", type: "image/png" },
    ],
    apple: "/header_mark_white.png",
  },
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="cs">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link
          href="https://fonts.googleapis.com/css2?family=Great+Vibes&family=Playfair+Display:wght@400;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen flex flex-col bg-gradient-to-b from-beige-800 via-beige-600 to-beige-400 overflow-x-hidden text-beige-50 w-full max-w-[100vw]">
        <CartProvider>
          <ServiceWorkerCleanup />
          <Navbar />
          <main className="flex-1 flex flex-col">
            {children}
          </main>
          <div
            className="w-full h-px bg-gradient-to-r from-transparent via-beige-200/40 to-transparent"
            aria-hidden="true"
          />
          <Footer />
          <WhatsAppWidget
            phone="420776479747"
            defaultMessage="Dobrý den, rád/a bych se zeptal/a na…"
            position="right"
          />
        </CartProvider>
      </body>
    </html>
  );
}
