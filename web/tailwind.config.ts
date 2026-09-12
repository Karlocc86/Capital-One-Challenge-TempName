import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        brand: {
          50: "#eef2f7",
          100: "#dbe3ee",
          400: "#3d5a80",
          600: "#1f3a5f",
          700: "#17304f",
          900: "#0c1a2e",
        },
        accent: {
          DEFAULT: "#c8102e",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(12, 26, 46, 0.06), 0 1px 6px rgba(12, 26, 46, 0.05)",
      },
    },
  },
  plugins: [],
};
export default config;
