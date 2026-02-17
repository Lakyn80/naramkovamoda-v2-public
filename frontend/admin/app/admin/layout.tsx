"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { buildApiUrl } from "../../lib/api";

const NAV_LINKS = [
  { href: "/admin/products", label: "📦 Produkty" },
  { href: "/admin/categories", label: "📂 Kategorie" },
  { href: "/admin/sold", label: "📊 Prodané" },
  { href: "/admin/payments", label: "💳 Platby" },
  { href: "/admin/media", label: "🖼️ Média" },
  { href: "/admin/media-inbox", label: "Media Inbox" },
];

export default function AdministraceLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(false);
  const [isAuthorized, setIsAuthorized] = useState(false);
  const isAuthRoute =
    pathname.startsWith("/admin/login") ||
    pathname.startsWith("/admin/forgot") ||
    pathname.startsWith("/admin/reset");

  useEffect(() => {
    if (isAuthRoute) {
      setCheckingAuth(false);
      setIsAuthorized(false);
      return;
    }
    let active = true;
    setCheckingAuth(true);
    fetch(buildApiUrl("/api/auth/me"))
      .then((res) => {
        if (!active) return;
        if (res.ok) {
          setIsAuthorized(true);
          return;
        }
        setIsAuthorized(false);
        router.replace("/admin/login");
      })
      .catch(() => {
        if (!active) return;
        setIsAuthorized(false);
        router.replace("/admin/login");
      })
      .finally(() => {
        if (active) setCheckingAuth(false);
      });
    return () => {
      active = false;
    };
  }, [isAuthRoute, router]);

  const handleLogout = async () => {
    setLogoutError(null);
    try {
      const res = await fetch(buildApiUrl("/api/auth/logout"), { method: "POST" });
      if (!res.ok) {
        throw new Error("Odhlášení se nezdařilo.");
      }
      router.push("/admin/login");
    } catch (err) {
      setLogoutError(err instanceof Error ? err.message : "Odhlášení se nezdařilo.");
    }
  };

  if (isAuthRoute) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-blue-600 to-sky-500 text-gray-900">
        {children}
      </div>
    );
  }

  if (checkingAuth || !isAuthorized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 text-gray-600">
        Načítám…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="fixed inset-x-0 top-0 z-30 bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 text-white shadow">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-3">
          <Link href="/admin" className="flex items-center gap-3 text-lg font-semibold">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/10">NM</span>
            <span>Admin</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-4 text-sm text-white/90">
            {NAV_LINKS.map((link) => (
              <Link key={link.href} href={link.href} className="hover:text-white">
                {link.label}
              </Link>
            ))}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full border border-white/30 px-3 py-1 text-sm hover:border-white/70 hover:text-white"
            >
              🚪 Odhlásit
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-8 pt-24">{children}</main>

      {logoutError && (
        <div className="fixed right-6 top-24 z-40 rounded-lg bg-red-600 px-4 py-3 text-sm text-white shadow-lg">
          {logoutError}
        </div>
      )}
    </div>
  );
}
