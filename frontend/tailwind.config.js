/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#fff4ef",
          100: "#ffe4d4",
          200: "#ffcaaa",
          300: "#ffa575",
          400: "#ff7a3d",
          500: "#ff6b15",   // ← acento principal
          600: "#f05208",
          700: "#c73e05",
          800: "#9e320b",
          900: "#7f2c0c",
        },
        ink: {
          DEFAULT: "#111111",
          muted:   "#6b7280",
          light:   "#9ca3af",
          xlight:  "#d1d5db",
        },
        surface: {
          DEFAULT: "#fafafa",
          white:   "#ffffff",
          raised:  "#f4f4f5",
          border:  "#e4e4e7",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "-apple-system", "BlinkMacSystemFont", '"Segoe UI"', "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        "card-hover": "0 4px 12px 0 rgb(0 0 0 / 0.08)",
      },
    },
  },
  plugins: [],
};
