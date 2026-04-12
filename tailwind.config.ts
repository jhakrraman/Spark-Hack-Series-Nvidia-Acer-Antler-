import type { Config } from "tailwindcss";

const config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
      },
      colors: {
        // DECK/01 tactical palette — rgb-triplet tokens so opacity modifiers work
        deck: {
          bg:        "rgb(var(--bg) / <alpha-value>)",
          elev:      "rgb(var(--bg-elev) / <alpha-value>)",
          panel:     "rgb(var(--bg-panel) / <alpha-value>)",
          fg:        "rgb(var(--fg) / <alpha-value>)",
          dim:       "rgb(var(--fg-dim) / <alpha-value>)",
          faint:     "rgb(var(--fg-faint) / <alpha-value>)",
          line:      "rgb(var(--border) / <alpha-value>)",
          linehi:    "rgb(var(--border-hi) / <alpha-value>)",
          signal:    "rgb(var(--signal) / <alpha-value>)",
          "signal-dim": "rgb(var(--signal-dim) / <alpha-value>)",
          alert:     "rgb(var(--alert) / <alpha-value>)",
          "alert-dim": "rgb(var(--alert-dim) / <alpha-value>)",
          ok:        "rgb(var(--ok) / <alpha-value>)",
          "ok-dim":  "rgb(var(--ok-dim) / <alpha-value>)",
        },
        // shadcn compat — reads the HSL vars from globals.css
        border: "hsl(var(--border-hsl))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "0px",
        md: "0px",
        sm: "0px",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
