/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: { brand: { 50: "#edf2ff", 100: "#dbe4ff", 500: "#4c6ef5", 600: "#3b5bdb", 700: "#364fc7" },
                violet: { 500: "#7950f2", 600: "#7048e8" } },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"] },
    },
  },
  plugins: [],
};
