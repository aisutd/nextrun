import { Platform, ViewStyle } from "react-native";
import { useApp } from "../state/AppState";
export const presets = [
  ["Orange", "#FF6A00"],
  ["Cyan", "#00E5FF"],
  ["Lime", "#B6FF00"],
  ["Magenta", "#FF2BD6"],
  ["Violet", "#9B5CFF"],
  ["Electric Blue", "#2E7BFF"],
  ["Hot Pink", "#FF3D81"],
];
export function rgba(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
}
export function mix(hex: string, other: string, amount: number) {
  const a = parseInt(hex.slice(1), 16),
    b = parseInt(other.slice(1), 16);
  return (
    "#" +
    [16, 8, 0]
      .map((n) =>
        Math.round(((a >> n) & 255) * amount + ((b >> n) & 255) * (1 - amount))
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")
  );
}
export function gradient(value: string): ViewStyle {
  return (
    Platform.OS === "web"
      ? { backgroundImage: value }
      : { experimental_backgroundImage: value }
  ) as ViewStyle;
}
export function useTheme() {
  const { s } = useApp(),
    light = s.theme === "light",
    n = parseInt(s.accent.slice(1), 16),
    on =
      0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255) > 150
        ? "#0A0A0A"
        : "#fff";
  return {
    light,
    accent: s.accent,
    on,
    bg: light ? "#fff" : "#050506",
    surface: light ? "#fff" : "#0b0b0c",
    surface2: light ? "#F2F3F5" : "#17171b",
    border: light ? "#E7E8EC" : rgba(s.accent, 0.38),
    text: light ? "#0A0A0A" : "#fff",
    muted: light ? "#5b6270" : "#9CA3AF",
    ring: light ? "#ECEDF0" : "rgba(255,255,255,.1)",
    darkAccent: mix(s.accent, "#000000", 0.6),
    shadow: light
      ? "0 10px 28px rgba(18,20,30,.07), 0 1px 2px rgba(18,20,30,.06)"
      : `0 0 0 1px ${rgba(s.accent, 0.07)}, 0 0 26px ${rgba(s.accent, 0.1)}`,
    glow: light
      ? `0 6px 18px ${rgba(s.accent, 0.35)}`
      : `0 0 18px ${rgba(s.accent, 0.5)}`,
  };
}
