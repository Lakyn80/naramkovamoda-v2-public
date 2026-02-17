"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function Hero() {
  const router = useRouter();

  const handleExploreClick = () => {
    router.push("/shop");
  };

  return (
    <section
      id="home"
      className="relative min-h-screen min-h-[100dvh] flex items-center justify-center px-4 sm:px-6 md:px-8 pt-24 pb-10 sm:pt-32 sm:pb-16 overflow-hidden"
        style={{
        backgroundImage: `
          radial-gradient(circle at top left, #433722 0%, #5c4a32 30%, transparent 60%),
          linear-gradient(to right, #7d6344, #9c7d5a, #d4c4a8)
        `,
      }}
    >
      <div className="backdrop-blur-sm bg-white/20 rounded-2xl p-6 sm:p-10 shadow-2xl w-full max-w-xl md:max-w-3xl text-center z-10">
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-white bg-clip-text text-transparent bg-gradient-to-r from-beige-200 via-beige-300 to-beige-200 drop-shadow-lg">
          Náramková Móda
        </h1>
        <p className="mt-4 text-lg sm:text-xl text-beige-100 font-medium">
          Ozdobte se jedinečností ✨
        </p>
        <button
          onClick={handleExploreClick}
          className="mt-8 w-full sm:w-auto px-8 py-3 bg-beige-600 hover:bg-beige-700 text-white font-semibold rounded-full shadow-lg transition duration-300"
        >
          Prozkoumat nabídku
        </button>
      </div>

      {/* Vlna dolů */}
      <svg
        className="absolute bottom-0 left-0 w-full pointer-events-none z-0"
        viewBox="0 0 1440 100"
        preserveAspectRatio="none"
      >
        <path
          fill="#f5f0e8"
          d="M0,40 C360,100 1080,0 1440,60 L1440,100 L0,100 Z"
        />
      </svg>
    </section>
  );
}
