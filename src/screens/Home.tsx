import React from "react";
import { View, Pressable } from "react-native";
import { useApp } from "../state/AppState";
import {
  Badge,
  Button,
  Card,
  Icon,
  IconButton,
  Label,
  Logo,
  Progress,
  Ring,
  Row,
  Scene,
  Section,
} from "../components/ui";
import { gradient, mix, useTheme } from "../theme/theme";
export function Home() {
  const { s, patch, go, card } = useApp(),
    t = useTheme();
  return (
    <>
      <Row between>
        <Logo />
        <View>
          <IconButton
            name="bell"
            label="Notifications"
            onPress={() => patch({ notifications: 0 })}
          />
          {s.notifications > 0 && (
            <Badge
              style={{
                position: "absolute",
                top: -6,
                right: -6,
                backgroundColor: t.accent,
                color: "#fff",
              }}
            >
              {s.notifications}
            </Badge>
          )}
        </View>
      </Row>
      <Label kind="hud" style={{ marginTop: 18 }}>
        Welcome back
      </Label>
      <Label kind="h1" style={{ marginTop: 2 }}>
        {s.handle || "Jordan"}
      </Label>
      <Label kind="muted" style={{ marginBottom: 14 }}>
        Keep pushing.
      </Label>
      <Scene
        name="arena"
        style={{
          height: 292,
          borderRadius: 26,
          paddingVertical: 22,
          paddingHorizontal: 20,
          borderWidth: 1,
          borderColor: t.border,
          boxShadow: t.shadow,
        }}
      >
        <Label kind="hud">The Locker Room</Label>
        <Label
          style={{
            fontFamily: "Montserrat_600",
            fontSize: 25,
            lineHeight: 32.5,
            letterSpacing: 4,
            marginTop: 12,
          }}
        >
          ANALYZE{"\n"}IMPROVE{"\n"}COMPETE
        </Label>
        <View
          style={{
            width: 32,
            height: 4,
            borderRadius: 2,
            marginTop: 16,
            backgroundColor: t.accent,
            boxShadow: t.glow,
          }}
        />
      </Scene>
      <Pressable
        accessibilityRole="button"
        onPress={() => go("cam")}
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: 14,
          marginHorizontal: 12,
          marginTop: -56,
          padding: 14,
          borderRadius: 22,
          borderWidth: 1,
          borderColor: t.border,
          backgroundColor: t.light
            ? "rgba(255,255,255,.84)"
            : "rgba(11,11,12,.84)",
          boxShadow: t.shadow,
        }}
      >
        <View
          style={[
            {
              width: 52,
              height: 52,
              borderRadius: 52,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: t.accent,
              boxShadow: t.glow,
            },
            gradient(
              `radial-gradient(circle at 35% 28%,${mix(t.accent, "#ffffff", 0.7)},${t.accent})`,
            ),
          ]}
        >
          <Icon name="arr" size={24} color={t.on} />
        </View>
        <View style={{ flex: 1 }}>
          <Label
            style={{
              fontFamily: "Inter_600",
              fontSize: 13,
              letterSpacing: 1.82,
            }}
          >
            START SESSION
          </Label>
          <Label
            kind="muted"
            style={{ fontSize: 12, lineHeight: 16.2, marginTop: 3 }}
          >
            Track your performance with AI powered analytics.
          </Label>
        </View>
      </Pressable>
      <Row style={{ gap: 8, marginVertical: 12 }}>
        {[
          ["cam", "Camera"],
          ["stat", "Stats"],
          ["fr", "Community"],
          ["me", "Profile"],
        ].map(([icon, label]) => (
          <Button
            key={label}
            style={{
              flex: 1,
              alignItems: "center",
              gap: 7,
              paddingTop: 13,
              paddingHorizontal: 4,
              paddingBottom: 11,
              borderRadius: 18,
              marginBottom: 0,
            }}
            onPress={() => {
              if (label === "Stats") {
                if (s.customCard) card({ flip: true });
                else patch({ flipped: true });
                go("me");
              } else
                go(
                  label === "Community"
                    ? "club"
                    : label === "Profile"
                      ? "me"
                      : "cam",
                );
            }}
          >
            <Icon name={icon} />
            <Label style={{ fontFamily: "Inter_500", fontSize: 11 }}>
              {label}
            </Label>
          </Button>
        ))}
      </Row>
      <Card>
        <Row between>
          <Label kind="h3">Your progress</Label>
          <Label kind="mono">Apr 26 · Pickup</Label>
        </Row>
        <Row style={{ gap: 18, marginTop: 12 }}>
          <Ring value={72} size={112} />
          <View style={{ flex: 1 }}>
            <Label kind="mono" style={{ marginBottom: 2 }}>
              LATEST GAME
            </Label>
            {[
              ["PTS", "18"],
              ["AST", "6"],
              ["REB", "4"],
            ].map(([k, v], i) => (
              <Row
                key={k}
                between
                style={{
                  paddingVertical: 7,
                  borderBottomWidth: i === 2 ? 0 : 1,
                  borderColor: t.border,
                  alignItems: "baseline",
                }}
              >
                <Label kind="mono">{k}</Label>
                <Label kind="h2" style={{ fontSize: 22 }}>
                  {v}
                </Label>
              </Row>
            ))}
          </View>
        </Row>
        <Row between style={{ marginTop: 12 }}>
          <Label kind="hud">Shooting efficiency</Label>
          <Label
            style={{ fontSize: 13, fontFamily: "Inter_600", color: t.accent }}
          >
            ▲ +4.2% vs last week
          </Label>
        </Row>
      </Card>
      <Section>Challenges</Section>
      <Card>
        {[
          ["Make 10 3PTs this week", 60],
          ["Log 3 sessions", 33],
          ["5 assists in one game", 100],
        ].map(([label, value], i) => (
          <View key={label} style={{ marginTop: i ? 14 : 0 }}>
            <Row between>
              <Label style={{ fontSize: 13 }}>{label}</Label>
              <Label kind="mono">{value}%</Label>
            </Row>
            <Progress value={Number(value)} />
          </View>
        ))}
      </Card>
    </>
  );
}
