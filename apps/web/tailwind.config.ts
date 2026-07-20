import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "Cambria", "serif"],
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        // Editorial "paper" palette — warm, calm, authoritative.
        paper: "#FBFAF7",
        card: "#FFFFFF",
        surface: "#F3F1EA",
        ink: "#1B1A17",
        muted: "#6B6760",
        faint: "#949087",
        line: "#E7E2D8",
        // Oxblood accent (law, seals) — not generic indigo.
        accent: "#7C2D2A",
        "accent-tint": "#F3E7E4",
        // Semantic trust-state colours, tuned for a light canvas.
        grounded: "#15803D",
        idk: "#B45309",
        partial: "#78716C",
      },
      boxShadow: {
        paper: "0 1px 2px rgba(27,26,23,0.04), 0 12px 28px -20px rgba(27,26,23,0.18)",
        lift: "0 2px 6px rgba(27,26,23,0.06), 0 18px 40px -24px rgba(27,26,23,0.22)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { "fade-in-up": "fade-in-up 0.4s cubic-bezier(0.22,1,0.36,1)" },
    },
  },
  plugins: [],
};

export default config;
