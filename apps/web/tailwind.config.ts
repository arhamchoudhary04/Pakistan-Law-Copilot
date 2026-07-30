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
        // Deep warm charcoal in four steps, so a card reads as a raised layer rather
        // than a border drawn on flat ground. Warm rather than blue-black, which keeps
        // the editorial character of the paper palette this replaced.
        // Named `canvas`, not `base`: Tailwind already owns `text-base` as a font-size,
        // so a `base` colour silently loses every `text-base` it is used in.
        canvas: "#100E0B",
        surface: "#191612",
        card: "#221E19",
        elevated: "#2E2822",
        line: "#352E26",
        "line-strong": "#4A4137",
        // Text ramp. Contrast against `canvas`: ink 16.9:1, muted 7.3:1, faint 5.2:1.
        ink: "#F4F0E8",
        muted: "#A69E94",
        faint: "#928A7E",
        // Muted brass: law and seals rather than a generic SaaS indigo, and light
        // enough to clear WCAG AA on every surface (7.2:1 on card).
        accent: "#C9A66B",
        "accent-hi": "#DCBE84",
        // Trust states, re-tuned for a dark canvas. `idk` is a clay red rather than an
        // amber on purpose, so a refusal never reads as brass chrome.
        grounded: "#71C48A",
        idk: "#D2795E",
        partial: "#9A9188",
      },
      boxShadow: {
        // The inset top highlight is what stops a dark card looking like flat paint.
        paper:
          "0 1px 2px rgba(0,0,0,0.45), 0 14px 30px -20px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.035)",
        lift: "0 4px 12px rgba(0,0,0,0.45), 0 28px 52px -26px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.055)",
        brass:
          "0 0 0 1px rgba(201,166,107,0.22), 0 10px 34px -14px rgba(201,166,107,0.24), inset 0 1px 0 rgba(255,255,255,0.06)",
      },
      backgroundImage: {
        sheen:
          "linear-gradient(135deg, rgba(201,166,107,0.13), rgba(201,166,107,0.03) 42%, transparent 70%)",
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
