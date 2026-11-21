import React, { useEffect, useRef, useState } from "react";
import { Text, View } from "react-native";
import { LiveEvent, liveFrame, LiveFrame, liveStart } from "../lib/api";
import { BONES, DetectChips, LiveStats, who, ZONE_COLOR } from "./LiveShared";

// Web build: the browser camera, streamed frame by frame through every backend model (players + pose,
// ball, rims, court, 2PT/3PT zones, ball holder), drawn live on top of the video. The session is also
// recorded, and handed to `onRecorded` when `active` turns off so it can go through the full upload pipeline.
const SEND_LONG_SIDE = 960;
type Props = { active: boolean; accent: string; onRecorded: (file: File) => void };

export function LiveCamera({ active, accent, onRecorded }: Props) {
  const video = useRef<HTMLVideoElement | null>(null),
    overlay = useRef<HTMLCanvasElement | null>(null),
    recorded = useRef(onRecorded);
  recorded.current = onRecorded;
  const [err, setErr] = useState(""),
    [aspect, setAspect] = useState(16 / 9),
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
    if (!active) return;
    let stop = false,
      stream: MediaStream | null = null,
      rec: MediaRecorder | null = null;
    const chunks: Blob[] = [];
    const grab = document.createElement("canvas");
    const times: number[] = [];

    async function loop() {
      const v = video.current!;
      while (!stop) {
        if (!v.videoWidth) {
          await new Promise((r) => setTimeout(r, 50));
          continue;
        }
        const s = Math.min(1, SEND_LONG_SIDE / Math.max(v.videoWidth, v.videoHeight));
        grab.width = Math.round(v.videoWidth * s);
        grab.height = Math.round(v.videoHeight * s);
        grab.getContext("2d")!.drawImage(v, 0, 0, grab.width, grab.height);
        const blob = await new Promise<Blob | null>((r) => grab.toBlob(r, "image/jpeg", 0.7));
        if (!blob || stop) continue;
        try {
          const f = await liveFrame(blob);
          if (stop) break;
          draw(overlay.current, f, accent);
          setLast(f);
          const now = performance.now();
          times.push(now);
          while (times.length && now - times[0] > 2000) times.shift();
          setFps(times.length / 2);
          setErr("");
        } catch (e) {
          setErr(`${(e as Error).message}. Is the NextRun API running?`);
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
    }

    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
      } catch (e) {
        setErr(`Camera unavailable: ${(e as Error).message}`);
        return;
      }
      if (stop) return stream.getTracks().forEach((t) => t.stop());
      const v = video.current!;
      v.srcObject = stream;
      v.onloadedmetadata = () => setAspect(v.videoWidth / v.videoHeight || 16 / 9);
      await v.play().catch(() => {});
      const mime = ["video/mp4", "video/webm;codecs=vp9", "video/webm"].find((m) => MediaRecorder.isTypeSupported(m));
      rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => {
        const type = rec!.mimeType || "video/webm";
        if (chunks.length)
          recorded.current(
            new File(chunks, `live-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.${type.includes("mp4") ? "mp4" : "webm"}`, { type }),
          );
      };
      rec.start(1000);
      try {
        await liveStart();
      } catch (e) {
        setErr(`${(e as Error).message}. Is the NextRun API running?`);
      }
      loop();
    })();

    return () => {
      stop = true;
      if (rec && rec.state !== "inactive") rec.stop();
      stream?.getTracks().forEach((t) => t.stop());
      setLast(null);
      seenShot.current = "";
    };
  }, [active]);

  if (!active) return null;
  return (
    <View style={{ marginBottom: 12 }}>
      <div style={{ position: "relative", width: "100%", aspectRatio: String(aspect), borderRadius: 24, overflow: "hidden", background: "#000" }}>
        <video ref={video} muted playsInline style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "fill" }} />
        <canvas ref={overlay} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
        <div style={{ position: "absolute", top: 10, left: 10, background: "rgba(0,0,0,.65)", color: "#ef4444", font: "600 11px Inter_600, system-ui", padding: "4px 8px", borderRadius: 999 }}>
          ● LIVE · {fps.toFixed(1)} fps{last ? ` · ${last.ms} ms` : ""}
        </div>
        {toast && (
          <div style={{ position: "absolute", left: "50%", top: "42%", transform: "translate(-50%,-50%)", padding: "8px 18px", borderRadius: 14, background: toast.made ? accent : "rgba(0,0,0,.75)", color: toast.made ? "#000" : "#fff", font: "800 22px Inter_600, system-ui", letterSpacing: 1, boxShadow: "0 6px 24px rgba(0,0,0,.35)" }}>
            {toast.made ? `MADE +${toast.points}${toast.three ? " · 3PT" : ""}` : "MISS"}
            {toast.player ? <span style={{ font: "600 12px system-ui", marginLeft: 8 }}>{who(toast.player)}</span> : null}
          </div>
        )}
        {game && (
          <div style={{ position: "absolute", top: 10, right: 10, background: "rgba(0,0,0,.65)", color: "#fff", font: "700 13px Inter_600, system-ui", padding: "4px 10px", borderRadius: 999 }}>
            {game.totals.points} PTS · {game.totals.makes}/{game.totals.shots} FG
          </div>
        )}
      </div>
      {err ? (
        <Text style={{ color: "#ef4444", marginTop: 8, fontSize: 12 }}>{err}</Text>
      ) : (
        <DetectChips last={last} accent={accent} />
      )}
      <LiveStats game={game} accent={accent} />
    </View>
  );
}

function draw(c: HTMLCanvasElement | null, f: LiveFrame, accent: string) {
  if (!c) return;
  if (c.width !== f.width || c.height !== f.height) {
    c.width = f.width;
    c.height = f.height;
  }
  const g = c.getContext("2d")!;
  const u = f.width / 640; // line widths scale with the frame
  g.clearRect(0, 0, c.width, c.height);
  g.lineJoin = "round";
  for (const r of f.rims) {
    const [x1, y1, x2, y2] = r.bbox;
    g.strokeStyle = r.agrees_with_court === false ? "#f97316aa" : "#f97316";
    g.lineWidth = 2.5 * u;
    g.strokeRect(x1, y1, x2 - x1, y2 - y1);
    label(g, r.hoop ? `HOOP ${r.hoop}` : "HOOP", x1, y1, "#f97316", u);
  }
  for (const p of f.players) {
    const [x1, y1, x2, y2] = p.bbox;
    const col = p.has_ball ? accent : (p.zone && ZONE_COLOR[p.zone]) || "#e5e7eb";
    if (p.keypoints) {
      g.strokeStyle = col + "cc";
      g.lineWidth = 2 * u;
      for (const [a, b] of BONES) {
        const A = p.keypoints[a], B = p.keypoints[b];
        if (A[2] < 0.3 || B[2] < 0.3) continue;
        g.beginPath();
        g.moveTo(A[0], A[1]);
        g.lineTo(B[0], B[1]);
        g.stroke();
      }
    }
    g.strokeStyle = col;
    g.lineWidth = (p.has_ball ? 3 : 1.8) * u;
    g.strokeRect(x1, y1, x2 - x1, y2 - y1);
    label(g, `#${p.track_id}${p.zone ? " " + p.zone : ""}${p.has_ball ? " ●" : ""}`, x1, y1, col, u);
  }
  for (const b of f.ball_candidates) {
    g.strokeStyle = "#facc1566";
    g.lineWidth = 1 * u;
    g.beginPath();
    g.arc(b.xy[0], b.xy[1], Math.max(4 * u, b.r), 0, Math.PI * 2);
    g.stroke();
  }
  if (f.ball) {
    g.strokeStyle = "#facc15";
    g.lineWidth = 3 * u;
    g.beginPath();
    g.arc(f.ball.xy[0], f.ball.xy[1], Math.max(6 * u, (f.ball.r ?? 6) + 3 * u), 0, Math.PI * 2);
    g.stroke();
  }
}

function label(g: CanvasRenderingContext2D, text: string, x: number, y: number, bg: string, u: number) {
  g.font = `600 ${Math.round(11 * u)}px system-ui`;
  const w = g.measureText(text).width + 8 * u, h = 15 * u;
  const ty = y - h < 0 ? y : y - h;
  g.fillStyle = bg;
  g.fillRect(x, ty, w, h);
  g.fillStyle = "#000";
  g.fillText(text, x + 4 * u, ty + 11 * u);
}
