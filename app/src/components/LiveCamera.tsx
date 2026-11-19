import React, { useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import Svg, { Circle, G, Line, Rect, Text as SvgText } from "react-native-svg";
import { GameStatus, LiveEvent, liveFrame, LiveFrame, liveSave, liveStart } from "../lib/api";
import { BONES, DetectChips, LiveStats, who, ZONE_COLOR } from "./LiveShared";

// Phone (iOS / Android, works in Expo Go): the back camera, photographed frame by frame and sent through every
// backend model (players + pose, ball, rims, court, 2PT/3PT zones, ball holder), drawn live on top of the preview.
// Expo Go cannot record video while grabbing frames, so the backend keeps the frames instead; when `active` turns
// off the session is saved as a game (POST /live/save) and handed to `onSaved` for the full analysis.
const SEND_LONG_SIDE = 960;

type Props = {
  active: boolean;
  accent: string;
  onRecorded: (file: File) => void; // web only
  onSaved?: (game: GameStatus) => void;
  onSaveError?: (message: string) => void;
};

export function LiveCamera({ active, accent, onSaved, onSaveError }: Props) {
  const cam = useRef<CameraView | null>(null),
    ready = useRef(false),
    saved = useRef(onSaved),
    failed = useRef(onSaveError);
  saved.current = onSaved;
  failed.current = onSaveError;
  const [permission, requestPermission] = useCameraPermissions();
  const granted = !!permission?.granted;
  const [err, setErr] = useState(""),
    [last, setLast] = useState<LiveFrame | null>(null),
    [fps, setFps] = useState(0),
    [toast, setToast] = useState<LiveEvent | null>(null),
    seenShot = useRef("");
  const game = last?.game ?? null;
  // newest shot; its verdict can flip (miss -> make) as later frames arrive, so the pop-up follows it
  const shot = game?.events.find((e) => e.type === "shot") ?? null;
  const shotKey = shot ? `${shot.t}-${shot.made}` : "";
  useEffect(() => {
    if (!shot || shotKey === seenShot.current) return;
    seenShot.current = shotKey;
    setToast(shot);
    const id = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(id);
  }, [shotKey]);

  useEffect(() => {
    if (active && permission && !permission.granted && permission.canAskAgain) requestPermission();
  }, [active, permission?.granted]);

  useEffect(() => {
    if (!active || !granted) return;
    let stop = false,
      started = false;
    const times: number[] = [];
    const t0 = Date.now();
    let sent = 0;

    async function loop() {
      while (!stop) {
        // onCameraReady does not always fire; after 2 s try anyway (takePictureAsync throws if it is not ready)
        if (!cam.current || (!ready.current && Date.now() - t0 < 2000)) {
          await new Promise((r) => setTimeout(r, 100));
          continue;
        }
        let stage = "taking a photo";
        try {
          const pic = await cam.current.takePictureAsync({ quality: 0.6, shutterSound: false });
          if (stop) break;
          stage = "resizing the photo";
          const big = Math.max(pic.width, pic.height);
          const resize =
            big > SEND_LONG_SIDE
              ? [{ resize: pic.width >= pic.height ? { width: SEND_LONG_SIDE } : { height: SEND_LONG_SIDE } }]
              : [];
          const small = await manipulateAsync(pic.uri, resize, { compress: 0.7, format: SaveFormat.JPEG });
          if (stop) break;
          stage = "sending the frame";
          const f = await liveFrame({ uri: small.uri });
          if (stop) break;
          if (!sent++) console.log(`[live] first frame analysed: ${f.width}x${f.height}, ${f.players.length} players`);
          setLast(f);
          const now = Date.now();
          times.push(now);
          while (times.length && now - times[0] > 3000) times.shift();
          setFps(times.length / 3);
          setErr("");
        } catch (e) {
          if (stop) break;
          const msg = (e as Error).message;
          console.warn(`[live] ${stage} failed: ${msg}`); // shows in the Metro log on the computer
          setErr(`Live detection stopped while ${stage}: ${msg}`);
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
    }

    (async () => {
      try {
        await liveStart(true);
        started = true;
        console.log("[live] session started");
      } catch (e) {
        console.warn(`[live] starting the session failed: ${(e as Error).message}`);
        setErr(`${(e as Error).message}. Is the NextRun API running?`);
      }
      if (!stop) loop();
    })();

    return () => {
      stop = true;
      setLast(null);
      setFps(0);
      seenShot.current = "";
      ready.current = false;
      if (!started) return;
      liveSave()
        .then((g) => saved.current?.(g))
        .catch((e) => failed.current?.((e as Error).message));
    };
  }, [active, granted]);

  if (!active) return null;
  if (!granted) {
    return (
      <View style={[styles.box, { borderColor: accent, marginBottom: 12 }]}>
        <Text style={{ color: accent, marginBottom: 10 }}>
          NextRun needs the camera to track the game live.
        </Text>
        {permission && !permission.canAskAgain ? (
          <Text style={{ color: "#888", fontSize: 12 }}>
            Camera access is turned off. Turn it on for Expo Go in your phone's Settings, then come back.
          </Text>
        ) : (
          <Pressable onPress={requestPermission} style={[styles.button, { backgroundColor: accent }]}>
            <Text style={{ color: "#000", fontWeight: "700" }}>Allow camera</Text>
          </Pressable>
        )}
      </View>
    );
  }

  const aspect = last ? last.width / last.height : 3 / 4;
  return (
    <View style={{ marginBottom: 12 }}>
      <View style={{ width: "100%", aspectRatio: aspect, borderRadius: 24, overflow: "hidden", backgroundColor: "#000" }}>
        <CameraView
          ref={cam}
          style={StyleSheet.absoluteFill}
          facing="back"
          animateShutter={false}
          onCameraReady={() => {
            ready.current = true;
            console.log("[live] camera ready");
          }}
          onMountError={(e) => {
            console.warn(`[live] camera failed to start: ${e.message}`);
            setErr(`Camera unavailable: ${e.message}`);
          }}
        />
        {last && <Overlay f={last} accent={accent} />}
        <Text style={[styles.pill, { top: 10, left: 10, color: "#ef4444" }]}>
          ● LIVE · {fps.toFixed(1)} fps{last ? ` · ${last.ms} ms` : ""}
        </Text>
        {game && (
          <Text style={[styles.pill, { top: 10, right: 10, color: "#fff" }]}>
            {game.totals.points} PTS · {game.totals.makes}/{game.totals.shots} FG
          </Text>
        )}
        {toast && (
          <View style={[styles.toast, { backgroundColor: toast.made ? accent : "rgba(0,0,0,.75)" }]}>
            <Text style={{ color: toast.made ? "#000" : "#fff", fontSize: 22, fontWeight: "800", letterSpacing: 1 }}>
              {toast.made ? `MADE +${toast.points}${toast.three ? " · 3PT" : ""}` : "MISS"}
              {toast.player ? <Text style={{ fontSize: 12, fontWeight: "600" }}>{`  ${who(toast.player)}`}</Text> : null}
            </Text>
          </View>
        )}
      </View>
      {err ? <Text style={{ color: "#ef4444", marginTop: 8, fontSize: 12 }}>{err}</Text> : <DetectChips last={last} accent={accent} />}
      <LiveStats game={game} accent={accent} />
    </View>
  );
}

// Boxes, skeletons, hoops and the ball, in the frame's own pixel coordinates (the SVG stretches to the preview).
function Overlay({ f, accent }: { f: LiveFrame; accent: string }) {
  const u = f.width / 640; // line widths scale with the frame
  return (
    <Svg style={StyleSheet.absoluteFill} viewBox={`0 0 ${f.width} ${f.height}`} preserveAspectRatio="none">
      {f.rims.map((r, i) => {
        const [x1, y1, x2, y2] = r.bbox;
        return (
          <G key={`r${i}`}>
            <Rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke="#f97316" strokeOpacity={r.agrees_with_court === false ? 0.6 : 1} strokeWidth={2.5 * u} />
            <Label text={r.hoop ? `HOOP ${r.hoop}` : "HOOP"} x={x1} y={y1} bg="#f97316" u={u} />
          </G>
        );
      })}
      {f.players.map((p) => {
        const [x1, y1, x2, y2] = p.bbox;
        const col = p.has_ball ? accent : (p.zone && ZONE_COLOR[p.zone]) || "#e5e7eb";
        const k = p.keypoints;
        return (
          <G key={`p${p.track_id}`}>
            {k &&
              BONES.map(([a, b]) =>
                k[a][2] < 0.3 || k[b][2] < 0.3 ? null : (
                  <Line key={`${a}-${b}`} x1={k[a][0]} y1={k[a][1]} x2={k[b][0]} y2={k[b][1]} stroke={col} strokeOpacity={0.8} strokeWidth={2 * u} />
                ),
              )}
            <Rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke={col} strokeWidth={(p.has_ball ? 3 : 1.8) * u} />
            <Label text={`#${p.track_id}${p.zone ? " " + p.zone : ""}${p.has_ball ? " ●" : ""}`} x={x1} y={y1} bg={col} u={u} />
          </G>
        );
      })}
      {f.ball_candidates.map((b, i) => (
        <Circle key={`c${i}`} cx={b.xy[0]} cy={b.xy[1]} r={Math.max(4 * u, b.r)} fill="none" stroke="#facc15" strokeOpacity={0.4} strokeWidth={u} />
      ))}
      {f.ball && (
        <Circle cx={f.ball.xy[0]} cy={f.ball.xy[1]} r={Math.max(6 * u, (f.ball.r ?? 6) + 3 * u)} fill="none" stroke="#facc15" strokeWidth={3 * u} />
      )}
    </Svg>
  );
}

function Label({ text, x, y, bg, u }: { text: string; x: number; y: number; bg: string; u: number }) {
  const h = 15 * u,
    w = text.length * 6.6 * u + 8 * u, // no text measuring in SVG: approximate the width from the length
    ty = y - h < 0 ? y : y - h;
  return (
    <G>
      <Rect x={x} y={ty} width={w} height={h} fill={bg} />
      <SvgText x={x + 4 * u} y={ty + 11 * u} fontSize={11 * u} fontWeight="600" fill="#000">
        {text}
      </SvgText>
    </G>
  );
}

const styles = StyleSheet.create({
  box: { padding: 16, borderRadius: 24, borderWidth: 1 },
  button: { alignSelf: "flex-start", paddingHorizontal: 16, paddingVertical: 10, borderRadius: 999 },
  pill: {
    position: "absolute",
    backgroundColor: "rgba(0,0,0,.65)",
    fontSize: 11,
    fontWeight: "700",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: "hidden",
  },
  toast: {
    position: "absolute",
    alignSelf: "center",
    top: "38%",
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: 14,
  },
});
