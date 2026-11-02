import React, { useRef } from "react";
import { Image, Pressable, View } from "react-native";
import { useApp } from "../state/AppState";
import {
  Button,
  Card,
  Chips,
  Label,
  Progress,
  Row,
  Toggle,
} from "../components/ui";
import { presets, gradient, rgba, useTheme } from "../theme/theme";
import { hueColor } from "../state/model";
import { artwork } from "../theme/artwork";
export function Settings() {
  const { s, patch, go } = useApp(),
    t = useTheme(),
    width = useRef(1);
  return (
    <>
      <Row style={{ marginBottom: 14 }}>
        <Button
          label="Back to profile"
          onPress={() => go("me")}
          style={{
            width: 42,
            height: 42,
            padding: 0,
            marginBottom: 0,
            borderRadius: 14,
            justifyContent: "center",
          }}
        >
          ‹
        </Button>
        <Label kind="h2">Settings</Label>
      </Row>
      <View
        style={[
          {
            height: 152,
            borderRadius: 24,
            overflow: "hidden",
            padding: 18,
            justifyContent: "flex-end",
            marginBottom: 12,
            borderWidth: 1,
            borderColor: t.border,
            boxShadow: t.shadow,
          },
          gradient(
            t.light
              ? `radial-gradient(120% 100% at 78% 10%,${rgba(t.accent, 0.38)},transparent 62%),linear-gradient(180deg,#fff,#fff3e8)`
              : `radial-gradient(120% 100% at 78% 10%,${rgba(t.accent, 0.55)},transparent 60%),linear-gradient(180deg,#15100b,#050505)`,
          ),
        ]}
      >
        <Image
          source={artwork.art}
          style={{
            position: "absolute",
            right: -26,
            top: -24,
            width: 190,
            height: 162,
            opacity: 0.95,
          }}
          resizeMode="contain"
        />
        <Label kind="hud">NextRun</Label>
        <Label kind="h2" style={{ marginTop: 2 }}>
          NextRun Lab
        </Label>
        <Label kind="muted" style={{ color: t.text, opacity: 0.8 }}>
          Turn on your potential.
        </Label>
      </View>
      <Card>
        <Row between>
          <View>
            <Label style={{ fontFamily: "Inter_600" }}>Light mode</Label>
            <Label kind="mono">Switch app theme</Label>
          </View>
          <Toggle
            label="Light mode"
            value={t.light}
            onChange={() => patch({ theme: t.light ? "dark" : "light" })}
          />
        </Row>
      </Card>
      <Card>
        <Label kind="h3">Accent color</Label>
        <Label kind="muted" style={{ marginTop: 4, marginBottom: 10 }}>
          Pick a neon color for buttons, glows and highlights. Orange is the
          default.
        </Label>
        <Chips
          compact
          values={presets.map((p) => p[0])}
          value={
            presets.find(
              (p) => p[1].toLowerCase() === s.accent.toLowerCase(),
            )?.[0] || ""
          }
          onChange={(v) =>
            patch({ accent: presets.find((p) => p[0] === v)![1], hue: 25 })
          }
        />
        <View
          accessibilityRole="adjustable"
          accessibilityLabel="Custom accent color"
          accessibilityValue={{ min: 0, max: 360, now: s.hue }}
          accessibilityActions={[{ name: "increment" }, { name: "decrement" }]}
          onAccessibilityAction={(e) => {
            const hue = Math.max(
              0,
              Math.min(
                360,
                s.hue + (e.nativeEvent.actionName === "increment" ? 5 : -5),
              ),
            );
            patch({ hue, accent: hueColor(hue) });
          }}
          onLayout={(e) => {
            width.current = e.nativeEvent.layout.width;
          }}
          onStartShouldSetResponder={() => true}
          onResponderGrant={(e) => {
            const hue = Math.round(
              Math.min(
                1,
                Math.max(0, e.nativeEvent.locationX / width.current),
              ) * 360,
            );
            patch({ hue, accent: hueColor(hue) });
          }}
          onResponderMove={(e) => {
            const hue = Math.round(
              Math.min(
                1,
                Math.max(0, e.nativeEvent.locationX / width.current),
              ) * 360,
            );
            patch({ hue, accent: hueColor(hue) });
          }}
          style={[
            { height: 12, borderRadius: 12, marginTop: 14 },
            gradient(
              "linear-gradient(90deg,#ff1744,#ff9100,#f6ff00,#00ff6a,#00e5ff,#2979ff,#d500f9,#ff1744)",
            ),
          ]}
        >
          <View
            style={{
              position: "absolute",
              top: -7,
              left: `${(s.hue / 360) * 94}%`,
              width: 26,
              height: 26,
              borderRadius: 26,
              backgroundColor: "#fff",
              borderWidth: 4,
              borderColor: t.accent,
              boxShadow: t.glow,
            }}
          />
        </View>
        <Label kind="mono" style={{ marginTop: 8 }}>
          Slide for any neon shade
        </Label>
      </Card>
      <Card>
        <Label kind="h3">Privacy</Label>
        <Label kind="muted" style={{ marginTop: 4, marginBottom: 10 }}>
          Who can see your profile and stats.
        </Label>
        <Chips
          values={["Public", "Club", "Private"]}
          value={s.privacy}
          onChange={(privacy) => patch({ privacy })}
        />
      </Card>
      <Card>
        <Pressable
          accessibilityRole="button"
          onPress={() => patch({ queueOpen: !s.queueOpen })}
        >
          <Row between>
            <Label kind="h3">Processing queue</Label>
            <BadgeLocal text={s.queueOpen ? "HIDE" : "2 UPLOADING"} />
          </Row>
        </Pressable>
        {s.queueOpen &&
          [
            ["Sat_run_full.mp4", 64],
            ["Drills_Tue.mp4", 18],
          ].map(([n, p]) => (
            <View key={n}>
              <Label kind="mono" style={{ marginTop: 12 }}>
                {n} — {p}%
              </Label>
              <Progress value={Number(p)} />
            </View>
          ))}
      </Card>
      <Card>
        <Label kind="h3">Legal</Label>
        <Label style={{ color: t.accent, marginTop: 8 }}>
          Terms of Service
        </Label>
        <Label style={{ color: t.accent, marginTop: 6 }}>Privacy Policy</Label>
      </Card>
      <Button
        style={{ borderColor: "#ef4444" }}
        textStyle={{ color: "#ef4444" }}
        onPress={() => patch({ deleteOpen: true })}
      >
        Delete account
      </Button>
      <Label kind="mono" style={{ textAlign: "center", marginTop: 6 }}>
        NextRun · Version 1.0.0
      </Label>
    </>
  );
}
import { Badge } from "../components/ui";
function BadgeLocal({ text }: { text: string }) {
  return <Badge>{text}</Badge>;
}
