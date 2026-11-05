import React, { useEffect, useState } from "react";
import { Image, Pressable, View } from "react-native";
import { useApp } from "../state/AppState";
import { formatTime } from "../state/model";
import {
  Avatar,
  Badge,
  Card,
  Chips,
  Label,
  Row,
  Scene,
} from "../components/ui";
import { Queue, UploadFootage } from "../components/UploadFootage";
import { useTheme } from "../theme/theme";
import { artwork } from "../theme/artwork";
export function Camera() {
  const { s, patch } = useApp(),
    t = useTheme(),
    [now, time] = useState(Date.now());
  useEffect(() => {
    if (!s.recording) return;
    const id = setInterval(() => time(Date.now()), 500);
    return () => clearInterval(id);
  }, [s.recording]);
  return (
    <>
      <Row between>
        <View>
          <Label kind="hud">Scouting</Label>
          <Label kind="h2">Scouting camera</Label>
        </View>
        <Badge
          style={
            s.recording
              ? { color: "#ef4444", borderColor: "#ef4444" }
              : undefined
          }
        >
          {s.recording ? "● REC" : "READY"}
        </Badge>
      </Row>
      <View style={{ marginTop: 14 }}>
        <Chips
          values={["Live", "Upload", "Library"]}
          value={s.cameraTab}
          onChange={(cameraTab) => patch({ cameraTab })}
        />
      </View>
      {s.cameraTab === "Upload" ? (
        <UploadFootage />
      ) : s.cameraTab === "Library" ? (
        <Queue />
      ) : (
        <>
          <Chips
            values={["Casual Pickup", "Tournament Game", "Solo Drills"]}
            value={s.mode}
            onChange={(mode) => patch({ mode })}
          />
          <Scene
            name="court"
            style={{
              height: 238,
              borderRadius: 24,
              borderWidth: 1,
              borderColor: t.border,
              boxShadow: t.shadow,
              marginBottom: 12,
            }}
          >
            <Image
              source={artwork["court-guide"]}
              style={{
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
              }}
              resizeMode="cover"
            />
            {[0, 1, 2, 3].map((i) => (
              <View
                key={i}
                style={{
                  position: "absolute",
                  width: 24,
                  height: 24,
                  borderColor: t.accent,
                  borderWidth: 2.5,
                  ...(i < 2
                    ? { top: 12, borderBottomWidth: 0 }
                    : { bottom: 12, borderTopWidth: 0 }),
                  ...(i % 2
                    ? { right: 12, borderLeftWidth: 0 }
                    : { left: 12, borderRightWidth: 0 }),
                  borderRadius: 9,
                }}
              />
            ))}
            <Badge
              style={{
                position: "absolute",
                top: 14,
                right: 44,
                backgroundColor: "#000",
                color: s.recording ? "#ef4444" : "#fff",
              }}
            >
              {s.recording
                ? `● REC 1080p · ${formatTime(Math.max(0, Math.floor((now - s.startedAt) / 1000)))}`
                : "READY 1080p"}
            </Badge>
            <Label
              kind="hud"
              style={{ position: "absolute", left: 44, bottom: 16 }}
            >
              Align court lines to guide
            </Label>
          </Scene>
          <Card>
            <Row between>
              <Label kind="h3">Roster</Label>
              <Label kind="mono">
                Team A ·{" "}
                {Object.values(s.roster).filter((x) => x === "A").length} | Team
                B · {Object.values(s.roster).filter((x) => x === "B").length}
              </Label>
            </Row>
            {Object.entries(s.roster).map(([name, team]) => (
              <Row
                key={name}
                between
                style={{
                  paddingVertical: 9,
                  borderTopWidth: 1,
                  borderColor: t.border,
                }}
              >
                <Row>
                  <Avatar size={34} style={{ borderRadius: 11 }} />
                  <Label>{name}</Label>
                </Row>
                <Row
                  style={{
                    gap: 3,
                    padding: 3,
                    borderRadius: 999,
                    borderWidth: 1,
                    borderColor: t.border,
                    backgroundColor: t.surface2,
                  }}
                >
                  {["", "A", "B"].map((v) => (
                    <Pressable
                      key={v}
                      accessibilityRole="button"
                      accessibilityLabel={`${name}: ${v ? "Team " + v : "Unassigned"}`}
                      accessibilityState={{ selected: v === team }}
                      onPress={() =>
                        patch({ roster: { ...s.roster, [name]: v } })
                      }
                      style={{
                        minWidth: 34,
                        paddingVertical: 7,
                        paddingHorizontal: 10,
                        borderRadius: 999,
                        backgroundColor:
                          team === v
                            ? v === "A"
                              ? t.accent
                              : v === "B"
                                ? t.text
                                : t.border
                            : "transparent",
                        boxShadow: team === v && v === "A" ? t.glow : undefined,
                      }}
                    >
                      <Label
                        style={{
                          fontSize: 11,
                          fontFamily: "Inter_600",
                          color:
                            team === v
                              ? v === "A"
                                ? t.on
                                : v === "B"
                                  ? t.bg
                                  : t.text
                              : t.muted,
                        }}
                      >
                        {v || "–"}
                      </Label>
                    </Pressable>
                  ))}
                </Row>
              </Row>
            ))}
          </Card>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={s.recording ? "Stop recording" : "Record"}
            onPress={() => {
              time(Date.now());
              patch({ recording: !s.recording, startedAt: Date.now() });
            }}
            style={{
              width: 84,
              height: 84,
              borderRadius: 84,
              borderWidth: 3,
              borderColor: t.accent,
              backgroundColor: t.surface,
              alignSelf: "center",
              marginVertical: 8,
              alignItems: "center",
              justifyContent: "center",
              boxShadow: t.glow,
            }}
          >
            <View
              style={{
                width: s.recording ? 28 : 56,
                height: s.recording ? 28 : 56,
                borderRadius: s.recording ? 7 : 56,
                backgroundColor: "#ef4444",
              }}
            />
          </Pressable>
          <Label kind="mono" style={{ textAlign: "center" }}>
            {s.recording
              ? `Recording ${s.mode}… tap to stop`
              : "Tap to start session"}
          </Label>
        </>
      )}
    </>
  );
}
