import React, { useEffect, useRef, useState } from "react";
import { Animated, GestureResponderEvent, Image, Pressable, Text, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { useApp } from "../state/AppState";
import { Button, Card, Label, Scene, Row, Badge, Progress } from "./ui";
import { artwork } from "../theme/artwork";
import { useTheme } from "../theme/theme";
import { ResultVideo } from "./ResultVideo";
import { GameDashboard } from "./GameDashboard";
import {
  fixCourt,
  frameUrl,
  GameStatus,
  getGame,
  listGames,
  previewUrl,
  uploadGame,
  videoUrl,
} from "../lib/api";

const STAGE: Record<GameStatus["status"], number> = {
  queued: 0,
  detecting: 0,
  calibrating: 1,
  analyzing: 2,
  rendering: 3,
  done: 4,
  failed: 4,
};
// One row per model / stage in the backend pipeline (nextrun_cv.pipeline).
const MODELS = [
  { key: "players", icon: "🏃", name: "Player pose + tracking", sub: "finds and follows every player", stage: 0 },
  { key: "ball", icon: "🏀", name: "Ball + rim detector", sub: "finds the ball and the hoops", stage: 0 },
  { key: "court", icon: "📐", name: "Court keypoints", sub: "fits the court lines", stage: 1 },
  { key: "events", icon: "⚡", name: "Fusion + events", sub: "shots · rebounds · assists · points", stage: 2 },
  { key: "render", icon: "🎬", name: "Overlay renderer", sub: "draws the annotated video", stage: 3 },
] as const;
const INK = "#0B1220",
  LINE = "#1E2A44",
  CYAN = "#22D3EE",
  GREEN = "#22C55E";

function detail(key: string, g: GameStatus): string {
  const n = Math.max(1, g.frames_done);
  if (key === "players") return `${g.max_players} players tracked`;
  if (key === "ball")
    return `ball in ${Math.round((100 * g.ball_frames) / n)}% of frames · rim in ${Math.round((100 * g.rim_frames) / n)}%`;
  if (key === "court")
    return g.court_method === "estimate"
      ? "court estimated from the scene"
      : g.court_calibrated
        ? `court locked${g.court_conf != null ? ` · conf ${g.court_conf.toFixed(2)}` : ""}`
        : "looking for the court";
  if (key === "events") return "scoring every shot, per player";
  return "boxes, names, points, ball trail";
}

function Pulse({ color }: { color: string }) {
  const v = useRef(new Animated.Value(0.3)).current;
  useEffect(() => {
    const a = Animated.loop(
      Animated.sequence([
        Animated.timing(v, { toValue: 1, duration: 600, useNativeDriver: false }),
        Animated.timing(v, { toValue: 0.3, duration: 600, useNativeDriver: false }),
      ]),
    );
    a.start();
    return () => a.stop();
  }, [v]);
  return <Animated.View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color, opacity: v, marginRight: 6 }} />;
}

function ModelRow({ m, g }: { m: (typeof MODELS)[number]; g: GameStatus }) {
  const at = STAGE[g.status],
    state = g.status === "failed" ? "wait" : at > m.stage ? "done" : at === m.stage ? "run" : "wait",
    pct = m.stage === 0 && g.frames_total ? (100 * g.frames_done) / g.frames_total : undefined,
    col = state === "done" ? GREEN : state === "run" ? CYAN : "#475569";
  return (
    <View style={{ paddingVertical: 10, borderTopWidth: 1, borderColor: LINE }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <View style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: LINE, alignItems: "center", justifyContent: "center", borderWidth: state === "run" ? 1 : 0, borderColor: CYAN }}>
          <Text style={{ fontSize: 18 }}>{m.icon}</Text>
        </View>
        <View style={{ flex: 1, marginLeft: 10 }}>
          <Text style={{ color: state === "wait" ? "#94A3B8" : "#F1F5F9", fontWeight: "800", fontSize: 14 }}>{m.name}</Text>
          <Text style={{ color: "#64748B", fontSize: 11, marginTop: 1 }}>{state === "wait" ? m.sub : detail(m.key, g)}</Text>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: col, borderRadius: 999, paddingHorizontal: 9, paddingVertical: 3 }}>
          {state === "run" && <Pulse color={CYAN} />}
          <Text style={{ color: col, fontSize: 10, fontWeight: "800" }}>{state === "done" ? "✓ DONE" : state === "run" ? "RUNNING" : "WAITING"}</Text>
        </View>
      </View>
      {state === "run" && pct !== undefined && (
        <View style={{ height: 4, borderRadius: 2, backgroundColor: LINE, marginTop: 8, overflow: "hidden" }}>
          <View style={{ width: `${pct}%`, height: 4, backgroundColor: CYAN }} />
        </View>
      )}
    </View>
  );
}

const CORNERS = [
  "Tap a baseline corner of the key (the painted box under the hoop)",
  "Tap the other baseline corner",
  "Tap the free-throw-line corner next to the one you just tapped",
  "Tap the last corner of the key",
];

// Optional: tap the 4 corners of the key once; the backend turns that into exact court lines (and re-renders the video).
function CourtFixer({ id, onApplied, onClose }: { id: string; onApplied: (g: GameStatus) => void; onClose: () => void }) {
  const t = useTheme();
  const [pts, setPts] = useState<{ x: number; y: number }[]>([]),
    [box, setBox] = useState({ w: 0, h: 0 }),
    [ratio, setRatio] = useState(16 / 9),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState("");
  useEffect(() => {
    Image.getSize(frameUrl(id), (w, h) => setRatio(w / h), () => {});
  }, [id]);
  function tap(e: GestureResponderEvent) {
    if (pts.length >= 4 || !box.w) return;
    const { locationX, locationY } = e.nativeEvent;
    setPts([...pts, { x: Math.min(1, Math.max(0, locationX / box.w)), y: Math.min(1, Math.max(0, locationY / box.h)) }]);
  }
  async function apply() {
    setBusy(true);
    setErr("");
    try {
      onApplied(await fixCourt(id, pts));
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <View style={{ marginTop: 12 }}>
      <Label kind="h3">Adjust the court lines</Label>
      <Label kind="muted" style={{ marginTop: 4 }}>
        {pts.length < 4 ? `${pts.length + 1}/4 · ${CORNERS[pts.length]}` : "Looks right? Apply to redraw the lines and the video."}
      </Label>
      <Pressable
        onPress={tap}
        onLayout={(e) => setBox({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}
        style={{ marginTop: 8, width: "100%", aspectRatio: ratio, borderRadius: 12, overflow: "hidden" }}
      >
        <Image source={{ uri: frameUrl(id) }} style={{ width: "100%", height: "100%" }} resizeMode="stretch" />
        {pts.map((p, i) => (
          <View
            key={i}
            pointerEvents="none"
            style={{ position: "absolute", left: p.x * box.w - 9, top: p.y * box.h - 9, width: 18, height: 18, borderRadius: 9, backgroundColor: t.accent, borderWidth: 2, borderColor: "#fff", alignItems: "center", justifyContent: "center" }}
          >
            <Text style={{ fontSize: 9, color: "#fff", fontWeight: "800" }}>{i + 1}</Text>
          </View>
        ))}
      </Pressable>
      {err ? <Label kind="muted" style={{ marginTop: 6 }}>{err}</Label> : null}
      <Row between style={{ marginTop: 10 }}>
        <Button onPress={() => setPts(pts.slice(0, -1))} disabled={!pts.length || busy} style={{ paddingVertical: 8 }} textStyle={{ fontSize: 12 }}>Undo</Button>
        <Button onPress={apply} disabled={pts.length < 4 || busy} style={{ paddingVertical: 8 }} textStyle={{ fontSize: 12 }}>{busy ? "Applying…" : "Apply"}</Button>
        <Button onPress={onClose} disabled={busy} style={{ paddingVertical: 8 }} textStyle={{ fontSize: 12 }}>Cancel</Button>
      </Row>
    </View>
  );
}

export function UploadFootage() {
  const { s, patch } = useApp();
  const [g, setG] = useState<GameStatus | null>(null),
    [err, setErr] = useState(""),
    [busy, setBusy] = useState(false),
    [tick, setTick] = useState(0),
    [fixing, setFixing] = useState(false);
  const id = s.gameId; // kept in app state, so leaving this tab does not lose the job

  async function choose() {
    const r = await DocumentPicker.getDocumentAsync({ type: "video/*", copyToCacheDirectory: true });
    if (r.canceled) return;
    const a = r.assets[0];
    setErr("");
    setBusy(true);
    try {
      const game = await uploadGame({ uri: a.uri, name: a.name, mimeType: a.mimeType, file: a.file });
      setG(game);
      patch({ gameId: game.id, uploadName: a.name });
    } catch (e) {
      setErr(`${(e as Error).message}. Is the NextRun API running?`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!id) return setG(null);
    getGame(id).then(setG).catch((e) => setErr((e as Error).message));
  }, [id]);
  const active = !!g && g.id === id && g.status !== "done" && g.status !== "failed";
  useEffect(() => {
    if (!id || !active) return;
    const timer = setInterval(async () => {
      try {
        setG(await getGame(id));
        setTick((n) => n + 1);
      } catch (e) {
        setErr((e as Error).message);
      }
    }, 600);
    return () => clearInterval(timer);
  }, [id, active]);

  const showPreview = !!g && active && g.frames_done > 0,
    label = g?.name || s.uploadName,
    estimated = !!g && g.status === "done" && (g.court_method === "estimate" || (g.court_conf ?? 0) < 0.5);
  return (
    <>
      <Card>
        <Label kind="h3" style={{ textAlign: "center" }}>Upload game footage</Label>
        {showPreview ? (
          <View style={{ marginTop: 8, borderRadius: 14, overflow: "hidden", backgroundColor: INK, aspectRatio: 16 / 9 }}>
            <Image source={{ uri: previewUrl(g!.id, tick) }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
            <View style={{ position: "absolute", top: 8, left: 8, flexDirection: "row", alignItems: "center", backgroundColor: "rgba(11,18,32,0.8)", borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 }}>
              <Pulse color="#EF4444" />
              <Text style={{ color: "#fff", fontSize: 10, fontWeight: "800", letterSpacing: 1 }}>LIVE VISION</Text>
            </View>
          </View>
        ) : (
          <Scene name="gate" style={{ height: 190, marginTop: 8, borderRadius: 14, overflow: "hidden" }}>
            <Image source={artwork["upload-hoop"]} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} resizeMode="contain" />
          </Scene>
        )}
        <Label kind="muted" style={{ textAlign: "center", marginTop: 6, marginBottom: 10 }}>
          {err
            ? err
            : busy
              ? "Uploading…"
              : g?.status === "failed"
                ? `Processing failed: ${g.error ?? "unknown error"}`
                : g?.status === "done"
                  ? `✓ ${label} processed`
                  : g
                    ? `${label} · ${Math.round(g.progress * 100)}%`
                    : "Choose a game video. The first 40 seconds are analyzed."}
        </Label>
        <Button onPress={choose} disabled={busy || active} style={{ borderRadius: 999, paddingVertical: 10, marginBottom: 0 }} textStyle={{ fontSize: 12 }}>
          {g ? "Choose another video" : "Choose video"}
        </Button>
      </Card>
      {g?.status === "done" && (
        <Card style={{ marginTop: 12 }}>
          <Label kind="h3">Annotated game video</Label>
          {g.has_video ? (
            <View style={{ marginTop: 10 }}>
              <ResultVideo uri={videoUrl(g.id, g.video_version)} />
            </View>
          ) : (
            <Label kind="muted" style={{ marginTop: 8 }}>
              The video could not be created{g.render_error ? `: ${g.render_error}` : ""}. Stats are below.
            </Label>
          )}
          {estimated && !fixing && (
            <Label kind="muted" style={{ marginTop: 8 }}>
              The court lines are an estimate for this video. You can fine-tune them if they look off.
            </Label>
          )}
          {fixing ? (
            <CourtFixer
              id={g.id}
              onClose={() => setFixing(false)}
              onApplied={(game) => {
                setG(game);
                setFixing(false);
              }}
            />
          ) : (
            <Button onPress={() => setFixing(true)} style={{ borderRadius: 999, paddingVertical: 8, marginTop: 10, marginBottom: 0 }} textStyle={{ fontSize: 12 }}>
              Adjust court lines
            </Button>
          )}
        </Card>
      )}
      {g?.status === "done" && <GameDashboard id={g.id} key={`${g.id}-${g.video_version}`} />}
      {g && (
        <View style={{ marginTop: 12, backgroundColor: INK, borderRadius: 20, padding: 14 }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <View>
              <Text style={{ color: "#F1F5F9", fontWeight: "800", fontSize: 16 }}>Models at work</Text>
              <Text style={{ color: "#64748B", fontSize: 11 }}>
                {g.frames_total ? `frame ${Math.min(g.frames_done, g.frames_total)} of ${g.frames_total}` : "starting up"}
              </Text>
            </View>
            <Text style={{ color: CYAN, fontWeight: "800", fontSize: 28 }}>{Math.round(g.progress * 100)}%</Text>
          </View>
          <View style={{ height: 6, borderRadius: 3, backgroundColor: LINE, marginTop: 10, marginBottom: 6, overflow: "hidden" }}>
            <View style={{ width: `${g.progress * 100}%`, height: 6, backgroundColor: g.status === "done" ? GREEN : CYAN }} />
          </View>
          {MODELS.map((m) => (
            <ModelRow key={m.key} m={m} g={g} />
          ))}
        </View>
      )}
    </>
  );
}
// Library tab: every upload the backend has kept. Tap one to open its video and stats again.
export function Queue() {
  const { s, patch } = useApp();
  const [games, setGames] = useState<GameStatus[] | null>(null),
    [err, setErr] = useState("");
  useEffect(() => {
    listGames().then(setGames).catch(() => setErr("Can't reach the NextRun API."));
  }, []);
  return (
    <Card>
      <Row between>
        <Label kind="h3">Your uploads</Label>
        <Badge>{games ? games.length : 0}</Badge>
      </Row>
      {err ? <Label kind="muted" style={{ marginTop: 10 }}>{err}</Label> : null}
      {games && games.length === 0 && <Label kind="muted" style={{ marginTop: 10 }}>Nothing yet. Upload a video first.</Label>}
      {(games ?? []).map((g) => (
        <Pressable
          key={g.id}
          accessibilityRole="button"
          onPress={() => patch({ gameId: g.id, uploadName: g.name, cameraTab: "Upload" })}
          style={{ marginTop: 12, opacity: g.id === s.gameId ? 1 : 0.9 }}
        >
          <Row between>
            <Label kind="mono" style={{ flex: 1 }}>{g.name || g.id}</Label>
            <Badge>{g.status === "done" ? "✓ DONE" : g.status === "failed" ? "FAILED" : `${Math.round(g.progress * 100)}%`}</Badge>
          </Row>
          {g.status !== "done" && g.status !== "failed" && <Progress value={g.progress * 100} />}
        </Pressable>
      ))}
    </Card>
  );
}
