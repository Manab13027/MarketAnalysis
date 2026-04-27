/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'JetBrains Mono'", "Menlo", "monospace"],
      },
      colors: {
        terminal: {
          bg:     "#0f1117",
          panel:  "#1a1f2e",
          border: "#2d3748",
          green:  "#22c55e",
          red:    "#ef4444",
          amber:  "#f59e0b",
          blue:   "#60a5fa",
          muted:  "#64748b",
          label:  "#94a3b8",
          text:   "#e2e8f0",
        }
      }
    }
  },
  plugins: [],
}

