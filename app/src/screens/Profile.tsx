import React from "react";
import { Image, View, StyleSheet } from "react-native";
import { useApp } from "../state/AppState";
import {
  Button,
  Card,
  Chips,
  Flip,
  Icon,
  IconButton,
  Label,
  Progress,
  Row,
  Scene,
  Section,
} from "../components/ui";
import { artwork } from "../theme/artwork";
import { gradient, rgba, useTheme } from "../theme/theme";
import { CustomPlayerCard } from "./CardBuilder";
export function Profile() {
  const { s, patch, go, card } = useApp(),
    t = useTheme(),
    border = s.border;
  const face = {
    flex: 1,
    borderRadius: 22,
    borderWidth: 3,
    borderColor: border,
    padding: 14,
    backgroundColor: "#0a0a0a",
    boxShadow: `0 0 28px ${border}, inset 0 0 30px rgba(0,0,0,.6)`,
  } as const;
  return (
    <>
      <Row between>
        <View>
          <Label kind="hud">Profile</Label>
          <Label kind="h2">Player card</Label>
        </View>
        <IconButton name="gear" label="Settings" onPress={() => go("set")} />
      </Row>
      <Scene
        name="net"
        style={{
          borderRadius: 24,
          paddingTop: 18,
          paddingBottom: 4,
          marginTop: 14,
          marginBottom: 10,
          borderWidth: 1,
          borderColor: t.border,
          boxShadow: t.shadow,
        }}
      >
        {s.customCard ? (
          <CustomPlayerCard />
        ) : (
          <Flip
            flipped={s.flipped}
            style={{ marginTop: 0 }}
            front={
              <View
                style={[
                  face,
                  gradient(
                    `radial-gradient(circle at 50% 30%,${border}55,#0a0a0a 70%)`,
                  ),
                ]}
              >
                <View
                  pointerEvents="none"
                  style={{
                    position: "absolute",
                    inset: 9,
                    borderRadius: 15,
                    borderWidth: 1,
                    borderColor: rgba(border, 0.5),
                  }}
                />
                <Row between style={{ alignItems: "flex-start" }}>
                  <View>
                    <Label
                      kind="mono"
                      style={{
                        color: "#fff",
                        opacity: 0.8,
                        letterSpacing: 2.2,
                      }}
                    >
                      OVR
                    </Label>
                    <Label
                      style={{
                        fontFamily: "Montserrat_800Italic",
                        fontSize: 46,
                        lineHeight: 46,
                        color: "#fff",
                      }}
                    >
                      92
                    </Label>
                  </View>
                  <Label
                    kind="mono"
                    style={{
                      color: "#fff",
                      borderWidth: 1,
                      borderColor: "rgba(255,255,255,.55)",
                      borderRadius: 6,
                      paddingVertical: 3,
                      paddingHorizontal: 8,
                    }}
                  >
                    PG
                  </Label>
                </Row>
                <View
                  style={{
                    height: 128,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Image
                    source={artwork["player-silhouette"]}
                    style={{
                      width: 96,
                      height: 112,
                      tintColor: border,
                      opacity: 0.92,
                    }}
                    resizeMode="contain"
                  />
                </View>
                <Label
                  style={{
                    fontFamily: "Montserrat_800Italic",
                    fontSize: 20,
                    color: "#fff",
                  }}
                >
                  {s.handle || "@playerone"}
                </Label>
                <Label kind="mono" style={{ color: border }}>
                  {s.title} · #24
                </Label>
              </View>
            }
            back={
              <View
                style={[
                  face,
                  gradient(
                    `radial-gradient(circle at 50% 30%,${border}33,#0a0a0a 70%)`,
                  ),
                ]}
              >
                <Label kind="h3" style={{ color: "#fff" }}>
                  Career
                </Label>
                <View
                  style={{
                    flexDirection: "row",
                    flexWrap: "wrap",
                    gap: 10,
                    marginTop: 12,
                  }}
                >
                  {[
                    ["62.5%", "FG"],
                    ["41.2%", "3PT"],
                    ["78.4%", "FT"],
                    ["18.6", "PPG"],
                    ["6.2", "APG"],
                    ["5.1", "RPG"],
                  ].map(([v, k]) => (
                    <View
                      key={k}
                      style={{
                        width: "47%",
                        flexGrow: 1,
                        backgroundColor: "rgba(255,255,255,.08)",
                        borderWidth: 1,
                        borderColor: t.border,
                        borderRadius: 14,
                        padding: 10,
                        alignItems: "center",
                      }}
                    >
                      <Label kind="h2" style={{ fontSize: 18, color: "#fff" }}>
                        {v}
                      </Label>
                      <Label
                        kind="mono"
                        style={{ fontFamily: "Inter_400", fontSize: 11 }}
                      >
                        {k}
                      </Label>
                    </View>
                  ))}
                </View>
              </View>
            }
          />
        )}
      </Scene>
      <Button
        onPress={() =>
          s.customCard
            ? card({ flip: !s.card.flip })
            : patch({ flipped: !s.flipped })
        }
      >
        Flip card
      </Button>
      <Button primary onPress={() => go("cardb")}>
        Build a custom card
      </Button>
      <Section>Attributes</Section>
      <Card>
        {[
          ["Shooting", 92],
          ["Playmaking", 88],
          ["Athleticism", 85],
          ["Defense", 78],
        ].map(([k, v], i) => (
          <View key={k} style={{ marginTop: i ? 12 : 0 }}>
            <Row between>
              <Label style={{ fontSize: 13 }}>{k}</Label>
              <Label kind="mono" style={{ color: t.text }}>
                {v}
              </Label>
            </Row>
            <Progress value={Number(v)} />
          </View>
        ))}
      </Card>
      <Section>Achievements</Section>
      <Card>
        <Row between style={{ gap: 6 }}>
          {[
            ["ball", "Sharpshooter"],
            ["bolt", "Quick hands"],
            ["trophy", "Champion"],
            ["flame", "On fire"],
          ].map(([i, k]) => (
            <View key={k} style={{ flex: 1, alignItems: "center" }}>
              <View
                style={{
                  width: 58,
                  height: 64,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Image
                  source={artwork.hexagon}
                  style={[
                    StyleSheet.absoluteFill,
                    { width: "100%", height: "100%" },
                  ]}
                  tintColor={t.accent}
                />
                <View
                  style={{
                    width: 49,
                    height: 49,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Icon name={i} size={24} />
                </View>
              </View>
              <Label
                kind="muted"
                style={{ fontSize: 10, marginTop: 6, textAlign: "center" }}
              >
                {k}
              </Label>
            </View>
          ))}
        </Row>
      </Card>
      <Section>Border glow</Section>
      <Chips
        compact
        values={["Orange", "Cyan", "Gold", "Violet"]}
        value={
          ["#FF6A00", "#22D3EE", "#FACC15", "#A855F7"].indexOf(s.border) >= 0
            ? ["Orange", "Cyan", "Gold", "Violet"][
                ["#FF6A00", "#22D3EE", "#FACC15", "#A855F7"].indexOf(s.border)
              ]
            : ""
        }
        onChange={(v) =>
          patch({
            border: {
              Orange: "#FF6A00",
              Cyan: "#22D3EE",
              Gold: "#FACC15",
              Violet: "#A855F7",
            }[v]!,
          })
        }
      />
      <Section>Title</Section>
      <Chips
        compact
        values={["Rookie", "Sniper", "Floor General", "Glass Cleaner"]}
        value={s.title}
        onChange={(title) => patch({ title })}
      />
      <Section>Recent activity</Section>
      {[
        ["Apr 26 · Pickup", "18 pts · 6 ast"],
        ["Apr 22 · Tournament", "24 pts · 4 ast"],
        ["Apr 19 · Solo drills", "82% FT"],
        ["Apr 15 · Pickup", "12 pts · 9 ast"],
      ].map(([k, v]) => (
        <Card key={k} style={{ paddingVertical: 12, marginBottom: 8 }}>
          <Row between>
            <Label style={{ fontSize: 13 }}>{k}</Label>
            <Label kind="mono">{v}</Label>
          </Row>
        </Card>
      ))}
    </>
  );
}
