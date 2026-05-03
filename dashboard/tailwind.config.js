/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: "#FFF9FB",
        peony: {
          DEFAULT: "#E8A0B0",
          700: "#C76B82",
          900: "#7A3345",
        },
        sage: {
          DEFAULT: "#9CAF88",
          900: "#3D4A32",
        },
        /** Matcha mint — inactive seasonal cards */
        matchamint: {
          DEFAULT: "#C5E0CD",
          light: "#E8F4EC",
          dark: "#8FB89A",
        },
        palegold: {
          DEFAULT: "#DCC48E",
          900: "#6B5B32",
        },
        /** Summer pastel — button gradient end */
        pastelyellow: {
          DEFAULT: "#FDEFC8",
          deep: "#F5E0A8",
        },
        /** Soft cocoa — headings */
        cocoa: "#5A4A42",
        /** CTA — hot pink per spec */
        hotpink: {
          DEFAULT: "#FF69B4",
          hover: "#FF7EC0",
          edge: "#E34A9A",
          ink: "#1F0512",
        },
      },
      fontFamily: {
        sans: ["Montserrat", "system-ui", "sans-serif"],
        heading: ['"DM Serif Display"', "Georgia", "serif"],
      },
      boxShadow: {
        glass: "0 12px 40px rgba(232, 160, 176, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.65)",
      },
    },
  },
  plugins: [],
};
