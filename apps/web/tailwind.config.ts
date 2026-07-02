import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Trust-first status palette, reused by badges + inspector.
        grounded: "#22c55e",
        idk: "#f59e0b",
        partial: "#94a3b8",
      },
    },
  },
  plugins: [],
};

export default config;
