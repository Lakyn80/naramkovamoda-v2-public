export default function LandingPage() {
  return (
    <section
      className="relative w-full flex-1 min-h-[55vh] sm:min-h-[65vh] md:min-h-[80vh] overflow-hidden"
      aria-label="Náramky pro radost"
    >
      <img
        src="/naramkyproradost.webp"
        alt=""
        className="absolute inset-0 w-full h-full object-cover"
      />

      <div className="absolute inset-0 flex flex-col items-center justify-center px-4 text-center -translate-y-6 sm:-translate-y-8 md:-translate-y-10">
        <h1 className="hero-title-script text-white">
          Náramky pro radost.
        </h1>

        <p className="hero-subtitle text-white mt-2 sm:mt-3">
          Dárek, který mluví za Vás.
        </p>

        <p className="hero-url text-white mt-1 sm:mt-2">
          naramkovamoda.cz
        </p>
      </div>
    </section>
  );
}
