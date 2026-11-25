/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f1a17",
        paper: "#f6f3ec",
        copper: {
          DEFAULT: "#9c4221",
          bright: "#b4532a",
        },
        pine: "#314232",
        line: "#e4dcd0",
      },
      fontFamily: {
        sans: ["Outfit", "sans-serif"],
        display: ["Fraunces", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(31, 26, 23, 0.05)",
      },
    },
  },
  plugins: [],
}
