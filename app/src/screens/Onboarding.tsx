import React, { useRef, useState } from "react";
import { View, Pressable, Image, useWindowDimensions } from "react-native";
import { GoogleMark } from "../components/GoogleMark";
import { Sweep } from "../components/Motion";
import { useApp } from "../state/AppState";
import { validHandle, normalizeHandle } from "../state/model";
import {
  Button,
  Dots,
  Icon,
  Input,
  Label,
  Logo,
  Row,
  Card,
  Progress,
} from "../components/ui";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme, gradient } from "../theme/theme";
import { artwork } from "../theme/artwork";
export const slides = [
  {
    scene: "dunk",
    tag: "Play",
    before: "YOUR JOURNEY BUILDS ",
    accent: "LEGENDS",
    text: "AI-powered basketball analytics, training, and community.",
  },
  {
    scene: "ball",
    tag: "Analyze",
    before: "ANALYZE. IMPROVE. ",
    accent: "CONNECT.",
    text: "The next generation of basketball performance and community.",
  },
  {
    scene: "comm",
    tag: "Connect",
    before: "BETTER PLAYERS BUILD STRONGER ",
    accent: "COMMUNITIES",
    text: "Train. Track. Compete. Together.",
  },
];
const tutorials = [
  [
    "Stand back",
    "Keep your phone steady at half-court height so the full court is visible.",
  ],
  [
    "Frame the lines",
    "Line the neon guides up with the baselines and sidelines.",
  ],
  ["Hit record", "Tap the red button. NextRun handles the tracking."],
];
export function Onboarding() {
  const { s, patch, go } = useApp(),
    t = useTheme(),
    window = useWindowDimensions(),
    insets = useSafeAreaInsets(),
    [handle, setHandle] = useState(s.handle),
    start = useRef(0);
  const advance = (d: number) => {
    if (s.route === "o0") patch({ onboarding: (s.onboarding + d + 3) % 3 });
    if (s.route === "o4")
      patch({ tutorial: Math.min(2, Math.max(0, s.tutorial + d)) });
  };
  if (s.route === "o0") {
    const o = slides[s.onboarding];
    return (
      <View
        style={{ flexGrow: 1 }}
        onTouchStart={(e) => {
          start.current = e.nativeEvent.pageX;
        }}
        onTouchEnd={(e) => {
          const d = e.nativeEvent.pageX - start.current;
          if (Math.abs(d) > 50) advance(d < 0 ? 1 : -1);
        }}
      >
        <View
          style={{
            paddingTop: 12,
            minHeight:
              (window.width >= 520
                ? Math.min(window.height - 32, 920) - 4
                : window.height - insets.top - insets.bottom) - 42,
          }}
        >
          <Row between>
            <Logo />
            <Label kind="hud">{o.tag}</Label>
          </Row>
          <View style={{ marginTop: "auto", paddingTop: 200 }}>
            <Row style={{ gap: 6, marginBottom: 6 }}>
              {slides.map((_, i) => (
                <Pressable
                  accessibilityLabel={`Slide ${i + 1}`}
                  accessibilityRole="button"
                  key={i}
                  onPress={() => patch({ onboarding: i })}
                  style={{
                    width: i === s.onboarding ? 42 : 24,
                    height: 16,
                    paddingVertical: 6,
                  }}
                >
                  <View
                    style={{
                      height: 4,
                      borderRadius: 6,
                      backgroundColor: i === s.onboarding ? t.accent : t.border,
                      boxShadow: i === s.onboarding ? t.glow : undefined,
                    }}
                  />
                </Pressable>
              ))}
            </Row>
            <Label
              kind="h1"
              style={{ fontSize: 35, lineHeight: 36.4, marginBottom: 10 }}
            >
              {o.before}
              <Label
                kind="h1"
                style={{ fontSize: 35, lineHeight: 36.4, color: t.accent }}
              >
                {o.accent}
              </Label>
            </Label>
            <Label kind="muted" style={{ marginBottom: 6 }}>
              {o.text}
            </Label>
            <Label kind="muted" style={{ marginBottom: 22 }}>
              Sign in to keep your stats and card.
            </Label>
            <Button primary onPress={() => go("o1")}>
              <Row style={{ justifyContent: "center" }}>
                <Icon name="mail" size={20} color={t.on} />
                <Label
                  style={{ fontFamily: "Inter_600", fontSize: 15, color: t.on }}
                >
                  Continue with email
                </Label>
              </Row>
            </Button>
            <Button onPress={() => go("o1")}>
              <Row style={{ justifyContent: "center" }}>
                <GoogleMark />
                <Label style={{ fontFamily: "Inter_600", fontSize: 15 }}>
                  Continue with Google
                </Label>
              </Row>
            </Button>
            <Button onPress={() => go("o1")} style={{ marginBottom: 0 }}>
              <Row style={{ justifyContent: "center" }}>
                <Image
                  source={artwork.apple}
                  style={{ width: 20, height: 20, tintColor: t.text }}
                />
                <Label style={{ fontFamily: "Inter_600", fontSize: 15 }}>
                  Continue with Apple
                </Label>
              </Row>
            </Button>
            <Label kind="mono" style={{ textAlign: "center", marginTop: 14 }}>
              Track. Improve. Compete. Together.
            </Label>
          </View>
        </View>
        <Dots index={0} />
      </View>
    );
  }
  if (s.route === "o1") {
    const ok = validHandle(handle);
    return (
      <>
        <Label kind="h1" style={{ marginTop: 30 }}>
          Create your player handle
        </Label>
        <Label kind="muted" style={{ marginTop: 8, marginBottom: 18 }}>
          This is permanent. You can't change it later.
        </Label>
        <View>
          <Input
            accessibilityLabel="Player handle"
            value={handle}
            onChangeText={(v) => {
              setHandle(v);
              patch({ handle: validHandle(v) ? normalizeHandle(v) : "" });
            }}
            maxLength={16}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="@playername"
          />
          {ok && (
            <Label
              style={{
                position: "absolute",
                right: 14,
                top: 12,
                color: t.accent,
              }}
            >
              ✓
            </Label>
          )}
        </View>
        <Label kind="mono" style={{ marginBottom: 14 }}>
          {ok
            ? "Looks good. This handle is yours for good."
            : "3–16 characters: letters, numbers, underscore."}
        </Label>
        <Button primary disabled={!ok} onPress={() => go("o2")}>
          Continue
        </Button>
        <Dots index={1} />
      </>
    );
  }
  if (s.route === "o2")
    return (
      <>
        <Label kind="h1" style={{ marginTop: 30, textAlign: "center" }}>
          Face scan
        </Label>
        <Label kind="muted" style={{ textAlign: "center" }}>
          Center your face so teammates can be tagged in footage.
        </Label>
        <View
          style={[
            {
              width: 200,
              height: 240,
              alignSelf: "center",
              marginVertical: 20,
              borderRadius: 22,
              borderWidth: 2,
              borderColor: t.accent,
              boxShadow: t.glow,
              overflow: "hidden",
              alignItems: "center",
              justifyContent: "center",
            },
            gradient("radial-gradient(circle at 50% 40%,#2a1505,#000)"),
          ]}
        >
          <Image
            source={artwork["face-scan"]}
            style={{
              width: 200,
              height: 240,
              tintColor: t.accent,
              opacity: 0.5,
            }}
          />
          <Sweep
            height={240}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 0,
              height: 3,
              backgroundColor: t.light ? "#0a2a5e" : "#22D3EE",
              boxShadow: "0 0 16px #22D3EE",
            }}
          />
        </View>
        <Progress value={s.scanned ? 100 : 60} />
        <Label
          kind="mono"
          style={{ textAlign: "center", marginTop: 10, marginBottom: 18 }}
        >
          {s.scanned ? "Face saved" : "Scanning…"}
        </Label>
        <Button primary disabled={!s.scanned} onPress={() => go("o3")}>
          Continue
        </Button>
        <Dots index={2} />
      </>
    );
  if (s.route === "o3")
    return (
      <>
        <Label kind="h1" style={{ marginTop: 30 }}>
          Find local clubs
        </Label>
        <Label kind="muted">
          Allow location to discover campus clubs and pickup groups near you.
        </Label>
        {s.location ? (
          <>
            <Card style={{ marginTop: 14 }}>
              <Label kind="h3">Near you</Label>
              {[
                "UT Dallas Hoops · 2.4 mi",
                "SMU Club Ball · 6.1 mi",
                "Dallas Pickup Crew · 3.3 mi",
              ].map((c) => (
                <Row
                  key={c}
                  between
                  style={{
                    paddingVertical: 10,
                    borderTopWidth: 1,
                    borderColor: t.border,
                  }}
                >
                  <Label>{c}</Label>
                  <Label kind="hud">JOIN</Label>
                </Row>
              ))}
            </Card>
            <Button primary onPress={() => go("o4")}>
              Continue
            </Button>
          </>
        ) : (
          <>
            <View
              style={[
                {
                  height: 170,
                  borderRadius: 16,
                  marginVertical: 16,
                  backgroundColor: t.surface2,
                  alignItems: "center",
                  justifyContent: "center",
                },
              ]}
            >
              {Array.from({ length: 7 }, (_, i) => (
                <View
                  key={"h" + i}
                  style={{
                    position: "absolute",
                    left: 0,
                    right: 0,
                    top: 24 + i * 25,
                    height: 1,
                    backgroundColor: t.border,
                  }}
                />
              ))}
              {Array.from({ length: Math.ceil(window.width / 25) }, (_, i) => (
                <View
                  key={"v" + i}
                  style={{
                    position: "absolute",
                    top: 0,
                    bottom: 0,
                    left: 24 + i * 25,
                    width: 1,
                    backgroundColor: t.border,
                  }}
                />
              ))}
              <Label style={{ fontSize: 34 }}>📍</Label>
            </View>
            <Button primary onPress={() => patch({ location: true })}>
              Allow location access
            </Button>
            <Button onPress={() => go("o4")}>Not now</Button>
          </>
        )}
        <Dots index={3} />
      </>
    );
  const tutorial = tutorials[s.tutorial];
  return (
    <>
      <Label kind="h1" style={{ marginTop: 20 }}>
        How to record
      </Label>
      <Pressable
        onPress={() => advance(1)}
        onTouchStart={(e) => {
          start.current = e.nativeEvent.pageX;
        }}
        onTouchEnd={(e) => {
          const d = e.nativeEvent.pageX - start.current;
          if (Math.abs(d) > 40) advance(d < 0 ? 1 : -1);
        }}
      >
        <Card
          style={{
            marginTop: 18,
            paddingVertical: 26,
            paddingHorizontal: 16,
            alignItems: "center",
          }}
        >
          <Image
            source={artwork["tutorial-court"]}
            style={{ width: 200, height: 117, tintColor: t.accent }}
          />
          <Label kind="h2" style={{ marginTop: 16, marginBottom: 6 }}>
            {tutorial[0]}
          </Label>
          <Label kind="muted" style={{ textAlign: "center" }}>
            {tutorial[1]}
          </Label>
          <Label kind="mono" style={{ marginTop: 12 }}>
            Swipe or tap to continue
          </Label>
        </Card>
      </Pressable>
      <Dots index={s.tutorial} total={3} />
      <Button
        primary
        onPress={() => (s.tutorial < 2 ? advance(1) : go("home"))}
      >
        {s.tutorial < 2 ? "Next" : "Got it"}
      </Button>
    </>
  );
}
