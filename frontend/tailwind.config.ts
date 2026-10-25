import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#fdfcfc",
        ink: "#201d1d",
        "ink-deep": "#0f0000",
        charcoal: "#302c2c",
        body: "#424245",
        mute: "#646262",
        stone: "#6e6e73",
        ash: "#9a9898",
        "surface-soft": "#f8f7f7",
        "surface-card": "#f1eeee",
        accent: "#007aff",
        warning: "#ff9f0a",
        danger: "#ff3b30",
        success: "#30d158"
      },
      borderColor: {
        hairline: "rgba(15,0,0,0.12)",
        "hairline-strong": "#646262"
      },
      borderRadius: {
        sm: "4px"
      },
      fontFamily: {
        mono: [
          "Berkeley Mono",
          "IBM Plex Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace"
        ]
      }
    }
  },
  plugins: []
};

export default config;
