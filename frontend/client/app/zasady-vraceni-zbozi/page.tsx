export default function ReturnPolicyPage() {
  return (
    <main className="min-h-screen bg-white/90 text-gray-900">
      <div className="mx-auto w-full max-w-3xl px-4 sm:px-6 md:px-8 pt-24 sm:pt-28 pb-10">
        <h1 className="text-2xl sm:text-3xl font-semibold">Zásady vrácení zboží</h1>

        <div className="mt-6 space-y-4 text-sm sm:text-base leading-relaxed">
          <h2 className="text-lg font-semibold">
            V souladu se zákonem č. 89/2012 Sb., občanský zákoník, má spotřebitel právo odstoupit od smlouvy uzavřené
            distančním způsobem (online objednávka) bez udání důvodu do 14 dnů od převzetí zboží.
          </h2>

          <p>
            Lhůta pro odstoupení od smlouvy začíná běžet dnem, kdy zákazník nebo jím určená třetí osoba (s výjimkou
            dopravce) zboží převezme.
          </p>

          <h2 className="text-lg font-semibold">
            Pro odstoupení od smlouvy musí zákazník informovat prodávajícího o svém rozhodnutí odstoupit od smlouvy
            jednoznačným prohlášením (např. e-mailem nebo písemně).
          </h2>

          <p>Zákazník může použít vzorový formulář pro odstoupení od smlouvy, není to však povinné.</p>

          <h2 className="text-lg font-semibold">
            Po odstoupení od smlouvy je zákazník povinen zaslat zboží zpět bez zbytečného odkladu, nejpozději do 14 dnů od
            oznámení odstoupení, na tuto adresu:
          </h2>

          <address className="not-italic">
            Marie Anna Stojaníková
            <br />
            Pod Svahy 990
            <br />
            686 01 Uherské Hradiště
            <br />
            Česká republika
          </address>

          <p>Zboží musí být vráceno kompletní, nepoškozené, pokud možno v původním obalu a s veškerým příslušenstvím.</p>

          <h2 className="text-lg font-semibold">
            Prodávající vrátí zákazníkovi všechny přijaté peněžní prostředky včetně nákladů na nejlevnější způsob dodání,
            a to bez zbytečného odkladu, nejpozději do 14 dnů od obdržení oznámení o odstoupení od smlouvy.
          </h2>

          <p>
            Vrácení peněz proběhne stejným způsobem platby, jaký zákazník použil při objednávce, pokud se strany
            nedohodnou jinak.
          </p>

          <p>Náklady na zpětné zaslání zboží nese zákazník, pokud nebylo dohodnuto jinak.</p>

          <p>
            Zákazník odpovídá za snížení hodnoty zboží v důsledku nakládání s ním jiným způsobem, než jaký je nutný k
            seznámení se s povahou a vlastnostmi zboží.
          </p>
        </div>
      </div>
    </main>
  );
}
