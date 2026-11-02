import React from "react";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useApp } from "../state/AppState";
import { Route } from "../state/model";
import { Icon, Label } from "./ui";
import { gradient, mix, rgba, useTheme } from "../theme/theme";
const tabs: [string, string, Route][] = [
  ["home", "Home", "home"],
  ["club", "Club Hub", "club"],
  ["cam", "", "cam"],
  ["fr", "Friends", "friends"],
  ["me", "Profile", "me"],
];
export function Navigation() {
  const { s, go } = useApp(),
    t = useTheme(),
    insets = useSafeAreaInsets();
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-around",
        marginHorizontal: 10,
        marginBottom: 10 + insets.bottom,
        paddingTop: 8,
        paddingHorizontal: 6,
        paddingBottom: 10,
        borderWidth: 1,
        borderColor: t.border,
        borderRadius: 28,
        backgroundColor: t.surface,
        boxShadow: t.shadow,
      }}
    >
      {tabs.map(([icon, label, route]) => {
        const selected =
            s.route === route ||
            (route === "me" && ["set", "cardb"].includes(s.route)),
          cam = route === "cam";
        return (
          <Pressable
            key={route}
            accessibilityRole="tab"
            accessibilityLabel={label || "Record"}
            accessibilityState={{ selected }}
            onPress={() => go(route)}
            style={[
              { minWidth: 52, alignItems: "center", gap: 3 },
              cam && {
                width: 58,
                height: 58,
                borderRadius: 58,
                backgroundColor: t.accent,
                marginTop: -28,
                justifyContent: "center",
                boxShadow: `0 0 0 6px ${t.surface}, 0 0 0 7px ${rgba(t.accent, 0.35)}, ${t.glow}`,
              },
              cam &&
                gradient(
                  `radial-gradient(circle at 35% 28%,${mix(t.accent, "#ffffff", 0.7)},${t.accent})`,
                ),
            ]}
          >
            <Icon
              name={icon}
              color={cam ? t.on : selected ? t.accent : t.muted}
            />
            {!!label && (
              <Label
                style={{
                  fontFamily: "Inter_500",
                  fontSize: 10,
                  color: selected ? t.accent : t.muted,
                }}
              >
                {label}
              </Label>
            )}
          </Pressable>
        );
      })}
    </View>
  );
}
