import React from "react";
import { Image, Pressable, StyleSheet, View, ScrollView } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { OutlineNumber } from "../components/OutlineNumber";
import { Hang } from "../components/Motion";
import { useApp } from "../state/AppState";
import {
  Button,
  Card,
  Chips,
  Flip,
  fontName,
  Input,
  Label,
  Row,
  Toggle,
} from "../components/ui";
import { Select } from "../components/Select";
import { ColorField } from "../components/ColorField";
import { artwork } from "../theme/artwork";
import { useTheme, gradient } from "../theme/theme";
export const shapes = [
  "Standard",
  "Rounded",
  "Arch",
  "Shield",
  "Tech",
  "Hex",
  "Slant",
];
export const typefaces = [
  "Montserrat",
  "Bebas Neue",
  "Orbitron",
  "Rajdhani",
  "Oswald",
  "Russo One",
  "Playfair Display",
  "Inter",
  "JetBrains Mono",
];
export const palettes = [
  ["#FF6A00", "#0A0A0A"],
  ["#00E5FF", "#0A0A2A"],
  ["#B6FF00", "#0A1A00"],
  ["#2E7BFF", "#050A24"],
  ["#FF2BD6", "#1A0020"],
  ["#FFD34E", "#2A1A00"],
  ["#E5E7EB", "#1F2937"],
];
export function CustomPlayerCard() {
  const { s, card } = useApp(),
    c = s.card,
    t = useTheme(),
    font = fontName(c.font);
  const base = (back = false) => (
    <View style={{ flex: 1 }}>
      <Image
        source={artwork[`shape-${c.shape}`]}
        style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
        tintColor={c.c2}
      />
      <Image
        source={artwork[`gradient-${c.shape}`]}
        style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
        tintColor={c.c1}
      />
      <Image
        source={artwork[`pattern-${c.shape}-${c.pattern}`]}
        style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
      />
      {!back && (
        <>
          <View
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 30,
              height: 200,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {c.image ? (
              <Image
                source={{ uri: c.image }}
                resizeMode="cover"
                style={{ width: "100%", height: 200 }}
              />
            ) : (
              <Image
                source={artwork["player-silhouette"]}
                style={{
                  width: 120,
                  height: 140,
                  tintColor: "#fff",
                  opacity: 0.35,
                }}
              />
            )}
          </View>
          <Image
            source={artwork[`fade-${c.shape}`]}
            style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
            tintColor="#000"
          />
          <View style={{ position: "absolute", left: 20, top: 18 }}>
            <Label
              style={{
                fontFamily: font,
                fontSize: 10,
                lineHeight: 10,
                letterSpacing: 2,
                color: "#fff",
                opacity: 0.85,
              }}
            >
              OVR
            </Label>
            <Label
              style={{
                fontFamily: font,
                fontSize: 38,
                lineHeight: 38,
                color: "#fff",
              }}
            >
              55
            </Label>
          </View>
          <Label
            style={{
              position: "absolute",
              right: 20,
              top: 20,
              fontFamily: font,
              fontSize: 12,
              letterSpacing: 1.68,
              paddingVertical: 3,
              paddingHorizontal: 8,
              borderWidth: 1,
              borderColor: "rgba(255,255,255,.7)",
              borderRadius: 6,
              color: "#fff",
            }}
          >
            {c.position}
          </Label>
          <Row
            between
            style={{
              position: "absolute",
              left: 22,
              right: 22,
              bottom: 22,
              gap: 6,
            }}
          >
            <View style={{ flex: 1 }}>
              <Label
                numberOfLines={1}
                style={{
                  fontFamily: font,
                  fontSize: 17,
                  lineHeight: 20,
                  letterSpacing: 0.68,
                  textTransform: "uppercase",
                  color: "#fff",
                }}
              >
                {c.name || s.handle || "@playerone"}
              </Label>
              <Label
                style={{
                  fontFamily: font,
                  fontSize: 10,
                  lineHeight: 13,
                  letterSpacing: 1.8,
                  textTransform: "uppercase",
                  opacity: 0.85,
                  color: "#fff",
                  marginTop: 2,
                }}
              >
                {c.title || "Rookie"}
              </Label>
            </View>
            <OutlineNumber text={"#" + c.num} font={font} fill={c.c2} />
          </Row>
        </>
      )}
      {back && (
        <>
          <View
            style={{
              position: "absolute",
              top: 24,
              left: 20,
              right: 20,
              alignItems: "center",
            }}
          >
            <Label
              numberOfLines={1}
              style={{
                fontFamily: font,
                fontSize: 16,
                letterSpacing: 0.64,
                color: "#fff",
                textTransform: "uppercase",
              }}
            >
              {c.name || s.handle || "@playerone"}
            </Label>
            <Label
              style={{
                fontFamily: font,
                fontSize: 10,
                letterSpacing: 1.8,
                color: "#fff",
                opacity: 0.85,
                marginTop: 2,
                textTransform: "uppercase",
              }}
            >
              {c.title || "Rookie"}
            </Label>
          </View>
          <View
            style={{
              position: "absolute",
              top: 78,
              left: 22,
              right: 22,
              flexDirection: "row",
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            {["PTS", "AST", "REB", "FG%", "STL", "BLK"].map((x) => (
              <View
                key={x}
                style={{
                  width: "47%",
                  flexGrow: 1,
                  backgroundColor: "rgba(0,0,0,.35)",
                  borderWidth: 1,
                  borderColor: t.border,
                  borderRadius: 14,
                  padding: 10,
                  alignItems: "center",
                }}
              >
                <Label
                  style={{ fontFamily: font, fontSize: 20, color: "#fff" }}
                >
                  0
                </Label>
                <Label
                  style={{
                    fontFamily: "Inter_400",
                    fontSize: 11,
                    color: "#fff",
                  }}
                >
                  {x}
                </Label>
              </View>
            ))}
          </View>
        </>
      )}
      <Image
        source={artwork[`frame-${c.shape}-${c.frame}`]}
        style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
      />
      {c.shine && (
        <View
          pointerEvents="none"
          style={[
            {
              position: "absolute",
              left: 18,
              top: 0,
              bottom: 0,
              width: 50,
              opacity: 0.25,
              transform: [{ skewX: "-20deg" }],
            },
            gradient(
              "linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent)",
            ),
          ]}
        />
      )}
    </View>
  );
  return (
    <Hang>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Flip player card"
        onPress={() => card({ flip: !c.flip })}
      >
        <Flip
          style={{ marginTop: 0 }}
          flipped={c.flip}
          front={base()}
          back={base(true)}
        />
      </Pressable>
    </Hang>
  );
}
export function CardBuilder() {
  const { s, patch, go, card } = useApp(),
    c = s.card;
  async function selfie() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 1,
    });
    if (!result.canceled) card({ image: result.assets[0].uri });
  }
  return (
    <>
      <Row style={{ marginBottom: 10 }}>
        <Button
          label="Back to profile"
          onPress={() => go("me")}
          style={{ width: 40, padding: 8, marginBottom: 0 }}
        >
          ‹
        </Button>
        <Label kind="h2">Custom card</Label>
      </Row>
      <CustomPlayerCard />
      <Label kind="mono" style={{ textAlign: "center", marginBottom: 12 }}>
        Tap the card to flip
      </Label>
      <Button primary onPress={selfie}>
        {c.image ? "Change selfie" : "Upload selfie"}
      </Button>
      <Card>
        <Label kind="h3">Identity</Label>
        <Input
          accessibilityLabel="Player name"
          placeholder="Player name"
          value={c.name}
          onChangeText={(name) => card({ name })}
          maxLength={18}
          style={{ marginTop: 10 }}
        />
        <Input
          accessibilityLabel="Card title"
          placeholder="Title (e.g. Sniper)"
          value={c.title}
          onChangeText={(title) => card({ title })}
          maxLength={22}
        />
        <View style={{ marginBottom: 10 }}>
          {" "}
          <Chips
            compact
            values={[
              "Rookie",
              "Sniper",
              "Floor General",
              "Glass Cleaner",
              "Lockdown",
              "Clutch Gene",
            ]}
            value={c.title}
            onChange={(title) => card({ title })}
          />
        </View>
        <Row>
          <Input
            accessibilityLabel="Jersey number"
            placeholder="#"
            value={c.num}
            onChangeText={(num) => card({ num })}
            maxLength={2}
            style={{ flex: 1, marginBottom: 0 }}
          />
          <View style={{ flex: 1 }}>
            <Select
              label="Position"
              values={["PG", "SG", "SF", "PF", "C"]}
              value={c.position}
              onChange={(position) => card({ position })}
            />
          </View>
        </Row>
      </Card>
      <Card>
        <Label kind="h3">Shape</Label>
        <View style={{ marginTop: 8 }}>
          <Chips
            compact
            values={shapes}
            value={c.shape}
            onChange={(shape) => card({ shape })}
          />
        </View>
        <Label kind="h3" style={{ marginTop: 12 }}>
          Design
        </Label>
        <View style={{ marginTop: 8 }}>
          <Chips
            compact
            values={[
              "Court",
              "Lines",
              "Dots",
              "Burst",
              "Grid",
              "Carbon",
              "None",
            ]}
            value={c.pattern}
            onChange={(pattern) => card({ pattern })}
          />
        </View>
        <Label kind="h3" style={{ marginTop: 12 }}>
          Frame
        </Label>
        <View style={{ marginTop: 8 }}>
          <Chips
            compact
            values={["Neon", "Double", "Chrome", "None"]}
            value={c.frame}
            onChange={(frame) => card({ frame })}
          />
        </View>
      </Card>
      <Card>
        <Label kind="h3">Typeface</Label>
        <View style={{ marginTop: 8 }}>
          <Chips
            compact
            font
            values={typefaces}
            value={c.font}
            onChange={(font) => card({ font })}
          />
        </View>
        <Label kind="h3" style={{ marginTop: 12 }}>
          Colors
        </Label>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8, paddingVertical: 8 }}
        >
          {palettes.map(([c1, c2]) => (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Palette ${c1}`}
              key={c1}
              onPress={() => card({ c1, c2 })}
              style={[
                { width: 46, height: 36, borderRadius: 999 },
                gradient(`linear-gradient(135deg,${c1},${c2})`),
              ]}
            />
          ))}
        </ScrollView>
        <Row style={{ marginTop: 10 }}>
          <Label kind="muted" style={{ flex: 1 }}>
            Custom colors
          </Label>
          <ColorField
            label="Primary card color"
            value={c.c1}
            onChange={(c1) => card({ c1 })}
          />
          <ColorField
            label="Secondary card color"
            value={c.c2}
            onChange={(c2) => card({ c2 })}
          />
        </Row>
        <Row between style={{ marginTop: 12 }}>
          <Label kind="muted">Holo shine</Label>
          <Toggle
            label="Holo shine"
            value={c.shine}
            onChange={() => card({ shine: !c.shine })}
          />
        </Row>
      </Card>
      <Button
        primary
        onPress={() => {
          patch({ customCard: true });
          go("me");
        }}
      >
        {s.customCard ? "✓ Using as my player card" : "Use as my player card"}
      </Button>
      {s.customCard && (
        <Button onPress={() => patch({ customCard: false })}>
          Back to default card
        </Button>
      )}
    </>
  );
}
