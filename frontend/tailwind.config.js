/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'Share Tech Mono'", "'IBM Plex Mono'", "'JetBrains Mono'", "Menlo", "monospace"],
        display: ["'VT323'", "'Share Tech Mono'", "'IBM Plex Mono'", "sans-serif"],
      },
      colors: {
        terminal: {
          bg:     "#020403",
          panel:  "#041108",
          border: "#1f4d2f",
          green:  "#4ade80",
          red:    "#f97373",
          amber:  "#c6f36b",
          blue:   "#6ee7a8",
          muted:  "#5f7a68",
          label:  "#93c5aa",
          text:   "#d7ffd6",
        }
      }
    }
  },
  plugins: [],
}

