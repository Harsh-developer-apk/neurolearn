/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        muted: "#64748b",
        line: "#d7deea",
        saffron: "#f28c28",
        indigo: "#1f4e79",
        teal: "#0f766e"
      }
    }
  },
  plugins: []
};
