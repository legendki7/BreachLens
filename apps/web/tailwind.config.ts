import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0A0A0B",
          900: "#101012",
          850: "#141416",
          800: "#19191C",
          700: "#222226",
          600: "#2C2C31",
          500: "#3A3A40",
          400: "#55555C",
        },
        bone: {
          50: "#F6F4EF",
          100: "#EDEAE4",
          200: "#CFCBC3",
          300: "#B4B0A8",
          400: "#9B978F",
        },
        // Sampled from the supplied BreachLens logo mark.
        signal: {
          DEFAULT: "#FD1822",
          text: "#FF5058",
          deep: "#9E0E16",
        },
        safe: "#5CCB8E",
        guard: "#E5AE45",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      maxWidth: {
        page: "75rem",
      },
    },
  },
  plugins: [],
};

export default config;
