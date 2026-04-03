import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary palette — deep forest green (trust, money, growth)
        primary: {
          DEFAULT: "#1B5E20",
          light: "#4CAF50",
          surface: "#E8F5E9",
          50: "#F1F8E9",
          100: "#DCEDC8",
          200: "#C5E1A5",
          600: "#43A047",
          700: "#388E3C",
          800: "#2E7D32",
          900: "#1B5E20",
        },
        // Accent palette — warm amber (energy, markets, warmth)
        accent: {
          DEFAULT: "#F57F17",
          light: "#FFF8E1",
          50: "#FFFDE7",
          100: "#FFF9C4",
          400: "#FFEE58",
          500: "#FFEB3B",
          600: "#FDD835",
          700: "#F9A825",
          800: "#F57F17",
          900: "#E65100",
        },
        // Neutrals
        surface: "#FFFFFF",
        background: "#FAFAF5",
        border: "#E0E0E0",
        // Semantic
        success: "#2E7D32",
        warning: "#F9A825",
        danger: "#C62828",
        // Text
        "text-primary": "#212121",
        "text-secondary": "#616161",
        "text-disabled": "#9E9E9E",
      },
      fontFamily: {
        sans: ["DM Sans", "system-ui", "-apple-system", "sans-serif"],
        mono: ["DM Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "1rem" }],
      },
      animation: {
        // Voice button listening pulse
        "pulse-ring": "pulse-ring 1.4s cubic-bezier(0.455, 0.03, 0.515, 0.955) infinite",
        // Transaction card slide-in
        "slide-in": "slide-in 0.3s ease-out forwards",
        // Loading dots
        "bounce-dot": "bounce-dot 1.4s ease-in-out infinite",
        // Checkmark flash
        "fade-in": "fade-in 0.2s ease-out forwards",
        // Count-up numbers
        "count-up": "count-up 0.6s ease-out forwards",
        // Waveform bars
        "wave-bar": "wave-bar 1.2s ease-in-out infinite",
        // Spin for processing
        "spin-slow": "spin 1.5s linear infinite",
        // Stagger fade-in for page load
        "stagger-in": "fade-in 0.4s ease-out forwards",
      },
      keyframes: {
        "pulse-ring": {
          "0%": {
            boxShadow:
              "0 0 0 0 rgba(245, 127, 23, 0.6), 0 0 0 0 rgba(245, 127, 23, 0.3)",
          },
          "70%": {
            boxShadow:
              "0 0 0 16px rgba(245, 127, 23, 0), 0 0 0 32px rgba(245, 127, 23, 0)",
          },
          "100%": {
            boxShadow:
              "0 0 0 0 rgba(245, 127, 23, 0), 0 0 0 0 rgba(245, 127, 23, 0)",
          },
        },
        "slide-in": {
          from: { transform: "translateY(-16px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        "bounce-dot": {
          "0%, 80%, 100%": { transform: "scale(0)", opacity: "0.3" },
          "40%": { transform: "scale(1)", opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "wave-bar": {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1.2)" },
        },
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)",
        "card-hover":
          "0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)",
        voice:
          "0 4px 14px rgba(27,94,32,0.35), 0 2px 6px rgba(27,94,32,0.2)",
        "voice-listening":
          "0 4px 20px rgba(245,127,23,0.45), 0 2px 8px rgba(245,127,23,0.25)",
      },
      screens: {
        xs: "480px",
      },
    },
  },
  plugins: [],
};

export default config;
