export const accent = "#FF6A00";
export const palettes = {
  light: {
    bg: "#ffffff",
    surface: "#ffffff",
    secondary: "#F2F3F5",
    border: "#E7E8EC",
    text: "#0A0A0A",
    muted: "#5b6270",
    edge: "rgba(255,106,0,.45)",
    track: "#ECEDF0",
    nav: "#ffffff",
  },
  dark: {
    bg: "#050506",
    surface: "#0d0d0f",
    secondary: "#17171b",
    border: "rgba(255,255,255,.09)",
    text: "#ffffff",
    muted: "#9CA3AF",
    edge: "rgba(255,106,0,.38)",
    track: "rgba(255,255,255,.1)",
    nav: "#0b0b0c",
  },
};
export type Theme = keyof typeof palettes;
export const typography = {
  body: "Inter-400",
  medium: "Inter-500",
  semibold: "Inter-600",
  heading: "Montserrat-Italic-800",
  display: "Montserrat-600",
  mono: "JetBrainsMono-500",
};
