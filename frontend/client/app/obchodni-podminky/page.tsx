import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-white/90 text-gray-900">
      <div className="mx-auto w-full max-w-3xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
        <h1 className="text-2xl sm:text-3xl font-semibold">Obchodní podmínky</h1>

        <div className="mt-6 space-y-4 text-sm sm:text-base leading-relaxed">
          <h2 className="text-lg font-semibold">
            <Link href="/zasady-vraceni-zbozi" className="underline underline-offset-4 decoration-beige-500/60 hover:text-beige-700">
              Zásady vrácení zboží
            </Link>
          </h2>
        </div>
      </div>
    </main>
  );
}
