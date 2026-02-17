import "./globals.css";
import ServiceWorkerRegister from "./ServiceWorkerRegister";

const STATIC_PREFIX = process.env.NODE_ENV === "production" ? "/admin" : "";

export const metadata = {
  title: "Náramková Móda Admin",
  manifest: `${STATIC_PREFIX}/manifest.json`,
  icons: {
    icon: [
      { url: `${STATIC_PREFIX}/icon_192.png`, sizes: "192x192", type: "image/png" },
      { url: `${STATIC_PREFIX}/icon_512.png`, sizes: "512x512", type: "image/png" },
      { url: `${STATIC_PREFIX}/favicon.ico`, sizes: "any" },
    ],
    apple: `${STATIC_PREFIX}/icon_192.png`,
  },
  themeColor: "#0f172a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="cs">
      <body className="min-h-screen bg-white text-black">
        {children}
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
