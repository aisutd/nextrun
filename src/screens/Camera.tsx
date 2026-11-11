import React, { useEffect, useState } from "react";
import { View, Pressable } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { useApp } from "../state/AppContext";
import {
  Art,
  Badge,
  Bar,
  Button,
  Card,
  Chips,
  Row,
  Segments,
  T,
} from "../components/ui";
import { accent } from "../theme/tokens";
export function UploadFootage() {
  const { data, setData } = useApp(),
    files = data.uploads,
    setFiles = (fn: (f: string[]) => string[]) =>
      setData((d) => ({ ...d, uploads: fn(d.uploads) })),
    [error, setError] = useState("");
  async function choose() {
    try {
      const r = await DocumentPicker.getDocumentAsync({
        type: "video/*",
        copyToCacheDirectory: true,
      });
      if (!r.canceled) setFiles((f) => [...f, r.assets[0].name]);
    } catch {
      setError("Could not open this video. Try again.");
    }
  }
  return (
    <Card style={{ alignItems: "center" }}>
      <T kind="h3">Upload game footage</T>
      <View
        style={{
          height: 190,
          width: "100%",
          marginTop: 8,
          borderRadius: 14,
          overflow: "hidden",
        }}
      >
        <Art name="gate" />
      </View>
      <T
        kind="muted"
        style={{ marginTop: 6, marginBottom: 10, textAlign: "center" }}
      >
        {files.length
          ? `✓ ${files.at(-1)} queued for processing`
          : "Drag a game video here or choose a file."}
      </T>
      <Button onPress={choose}>Choose video</Button>
      {!!error && <T style={{ color: "#ef4444" }}>{error}</T>}
      {files.map((f, i) => (
        <View key={i} style={{ width: "100%" }}>
          <T kind="mono">{f} — queued</T>
          <Bar value={0.03} />
        </View>
      ))}
    </Card>
  );
}
export function Camera() {
  const { data, colors, go, setHistoryTab, setLogging, completeQuest } =
      useApp(),
    [tab, setTab] = useState("Live"),
    [mode, setMode] = useState("Casual Pickup"),
    [rec, setRec] = useState(false),
    [seconds, setSeconds] = useState(0),
    [roster, setRoster] = useState<Record<string, string>>({});
  useEffect(() => {
    if (!rec) return;
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [rec]);
  const time = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  return (
    <>
      <Row style={{ justifyContent: "space-between" }}>
        <View>
          <T kind="hud">Scouting</T>
          <T kind="h2">Scouting camera</T>
        </View>
        <Badge>{rec ? "● REC" : "READY"}</Badge>
      </Row>
      <View style={{ marginTop: 14 }}>
        <Segments
          options={["Live", "Upload", "Library"]}
          value={tab}
          onChange={setTab}
        />
      </View>
      <Card>
        <T kind="hud">Heads up</T>
        <T kind="muted" style={{ marginTop: 4, marginBottom: 8 }}>
          Recording does not produce stats yet. Log your games by hand to earn
          XP, MVPs and titles.
        </T>
        <Button
          style={{
            alignSelf: "flex-start",
            marginBottom: 0,
            paddingVertical: 10,
          }}
          onPress={() => {
            setLogging(true);
            setHistoryTab("Sessions");
            go("history");
          }}
        >
          Log a game
        </Button>
      </Card>
      {tab === "Upload" ? (
        <UploadFootage />
      ) : tab === "Library" ? (
        <Card>
          <Row style={{ justifyContent: "space-between" }}>
            <T kind="h3">Processing queue</T>
            <Badge>{data.uploads.length} IN QUEUE</Badge>
          </Row>
          {data.uploads.map((f, i) => (
            <View key={i} style={{ marginTop: 12 }}>
              <T kind="mono">{f} — queued</T>
              <Bar value={0.03} />
            </View>
          ))}
        </Card>
      ) : (
        <>
          <Segments
            options={["Casual Pickup", "Tournament Game", "Solo Drills"]}
            value={mode}
            onChange={setMode}
          />
          <View
            style={{
              height: 238,
              borderRadius: 24,
              borderWidth: 1,
              borderColor: colors.edge,
              overflow: "hidden",
              marginBottom: 12,
            }}
          >
            <Art name="court" />
            <Art
              name="court-guide"
              resizeMode="stretch"
              style={{
                position: "absolute",
                inset: 0,
                width: undefined,
                height: undefined,
              }}
            />
            {[
              [12, 12],
              [undefined, 12],
              [12, undefined],
              [undefined, undefined],
            ].map(([l, t], i) => (
              <View
                key={i}
                style={{
                  position: "absolute",
                  left: l,
                  top: t,
                  right: l === undefined ? 12 : undefined,
                  bottom: t === undefined ? 12 : undefined,
                  width: 24,
                  height: 24,
                  borderWidth: 2.5,
                  borderColor: accent,
                  borderRightWidth: l ? 0 : 2.5,
                  borderLeftWidth: l ? 2.5 : 0,
                  borderBottomWidth: t ? 0 : 2.5,
                  borderTopWidth: t ? 2.5 : 0,
                }}
              />
            ))}
            <View style={{ position: "absolute", right: 44, top: 14 }}>
              <Badge>{rec ? `● REC 1080p · ${time}` : "READY 1080p"}</Badge>
            </View>
            <T
              kind="hud"
              style={{ position: "absolute", left: 44, bottom: 16 }}
            >
              Align court lines to guide
            </T>
          </View>
          <Card>
            <Row style={{ justifyContent: "space-between" }}>
              <T kind="h3">Roster</T>
              <T kind="mono">
                Team A · {Object.values(roster).filter((v) => v === "A").length}{" "}
                | Team B ·{" "}
                {Object.values(roster).filter((v) => v === "B").length}
              </T>
            </Row>
            {data.friends.map((f) => (
              <Row
                key={f.name}
                style={{
                  paddingVertical: 9,
                  justifyContent: "space-between",
                  borderTopWidth: 1,
                  borderTopColor: colors.border,
                }}
              >
                <T>{f.name}</T>
                <Chips
                  options={["–", "A", "B"]}
                  value={roster[f.name] || "–"}
                  onChange={(v) => setRoster((r) => ({ ...r, [f.name]: v }))}
                />
              </Row>
            ))}
          </Card>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={rec ? "Stop recording" : "Start session"}
            onPress={() => {
              if (rec) completeQuest("rec");
              else setSeconds(0);
              setRec(!rec);
            }}
            style={{
              width: 84,
              height: 84,
              borderRadius: 84,
              borderWidth: 3,
              borderColor: accent,
              backgroundColor: colors.surface,
              alignSelf: "center",
              alignItems: "center",
              justifyContent: "center",
              marginVertical: 8,
            }}
          >
            <View
              style={{
                width: rec ? 28 : 56,
                height: rec ? 28 : 56,
                borderRadius: rec ? 7 : 56,
                backgroundColor: "#ef4444",
              }}
            />
          </Pressable>
          <T kind="mono" style={{ textAlign: "center" }}>
            {rec ? `Recording ${mode}… tap to stop` : "Tap to start session"}
          </T>
        </>
      )}
    </>
  );
}
