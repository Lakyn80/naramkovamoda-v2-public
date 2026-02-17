import Link from "next/link";

export default function AdminHomePage() {
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold">Přehled administrace</h2>
      <p className="text-sm text-gray-600">Rychlé odkazy na hlavní sekce.</p>
      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          href="/admin/products"
          className="rounded-lg border border-gray-200 bg-white p-4 text-sm hover:border-gray-300"
        >
          Produkty
        </Link>
        <Link
          href="/admin/categories"
          className="rounded-lg border border-gray-200 bg-white p-4 text-sm hover:border-gray-300"
        >
          Kategorie
        </Link>
        <Link
          href="/admin/media"
          className="rounded-lg border border-gray-200 bg-white p-4 text-sm hover:border-gray-300"
        >
          Média
        </Link>
      </div>
    </div>
  );
}
