export default function PrivacyPolicyPage() {
  return (
    <main className="min-h-screen bg-white/90 text-gray-900">
      <div className="mx-auto w-full max-w-3xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
        <h1 className="text-2xl sm:text-3xl font-semibold">Ochrana osobních údajů (GDPR)</h1>

        <div className="mt-6 space-y-4 text-sm sm:text-base leading-relaxed">
          <h2 className="text-lg font-semibold">Informace o zpracování osobních údajů</h2>
          <p>Správce: Náramková Móda, kontakt naramkovamoda@email.cz, +420 776 47 97 47.</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Účel: vyřízení objednávek, komunikace, účetní evidence.</li>
            <li>Právní základ: plnění smlouvy, oprávněný zájem.</li>
            <li>Práva subjektu: přístup, oprava, výmaz, omezení.</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
