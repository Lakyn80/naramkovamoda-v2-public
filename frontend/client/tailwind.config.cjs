/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        beige: {
          50: "#faf8f5",
          100: "#f5f0e8",
          200: "#e8dfd0",
          300: "#d4c4a8",
          400: "#b8a078",
          500: "#9c7d5a",
          600: "#7d6344",
          700: "#5c4a32",
          800: "#433722",
          900: "#2d2518",
          950: "#1a1510",
        },
      },
    },
  },
  plugins: []
}
