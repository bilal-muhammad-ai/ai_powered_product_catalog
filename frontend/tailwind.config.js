/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f1a17",
        paper: "#f3efe6",
        copper: {
          DEFAULT: "#9c4221",
          bright: "#b4532a",
        },
        pine: "#314232",
        line: "#ddd4c6",
      },
      fontFamily: {
        sans: ["Outfit", "sans-serif"],
        display: ["Fraunces", "serif"],
      },
    },
  },
  plugins: [],
}
