import { Platform } from "react-native";
// Set EXPO_PUBLIC_API_URL to the machine running `uvicorn nextrun_cv.api:app --host 0.0.0.0`
// (a phone needs your computer's LAN IP, e.g. http://192.168.1.20:8000).
export const API =
  process.env.EXPO_PUBLIC_API_URL ??
  (Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000");
export type GameStatus = {
  id: string;
  status:
    | "queued"
    | "detecting"
    | "calibrating"
    | "analyzing"
    | "rendering"
    | "done"
    | "failed";
  error: string | null;
  court_calibrated: boolean;
  court_conf: number | null;
  progress: number;
  frames_done: number;
  frames_total: number;
  max_players: number;
  ball_frames: number;
  rim_frames: number;
  has_video: boolean;
  render_error: string | null;
  video_version: number;
  court_method: string | null;
  name: string;
};
export type BoxScore = {
  headline: string[];
  players: Record<string, string | number | null>[];
};
export type Picked = { uri: string; name: string; mimeType?: string; file?: File };
export async function uploadGame(v: Picked): Promise<GameStatus> {
  const body = new FormData();
  if (Platform.OS === "web" && v.file) body.append("video", v.file, v.name);
  else
    body.append("video", {
      uri: v.uri,
      name: v.name,
      type: v.mimeType ?? "video/mp4",
    } as unknown as Blob);
  const r = await fetch(`${API}/games`, { method: "POST", body });
  if (!r.ok) throw new Error(`Upload failed (${r.status})`);
  return r.json();
}
export async function getGame(id: string): Promise<GameStatus> {
  const r = await fetch(`${API}/games/${id}`);
  if (!r.ok) throw new Error(`Status failed (${r.status})`);
  return r.json();
}
export async function listGames(): Promise<GameStatus[]> {
  const r = await fetch(`${API}/games`);
  if (!r.ok) throw new Error(`List failed (${r.status})`);
  return r.json();
}
export async function getStats(id: string): Promise<BoxScore | null> {
  const r = await fetch(`${API}/games/${id}/stats`);
  return r.ok ? r.json() : null;
}
export const previewUrl = (id: string, tick: number) =>
  `${API}/games/${id}/preview?t=${tick}`;
export const videoUrl = (id: string, v = 0) => `${API}/games/${id}/video?v=${v}`;
export const frameUrl = (id: string) => `${API}/games/${id}/frame`;
export async function fixCourt(id: string, points: { x: number; y: number }[]): Promise<GameStatus> {
  const r = await fetch(`${API}/games/${id}/court`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ points: points.map((p) => [p.x, p.y]) }),
  });
  if (!r.ok) throw new Error(`Court fix failed (${r.status})`);
  return r.json();
}
export type Card = {
  player: string;
  team: string | null;
  PTS: number;
  REB: number;
  AST: number;
  STL: number;
  TOV: number;
  FGM: number;
  FGA: number;
  "3PM": number;
  "3PA": number;
  RATING: number;
  rank: number;
  xp: number;
  level: number;
  badges: string[];
  shots: { t: number; made: boolean; three: boolean; points: number }[];
};
// One shot in game order. `score` is the running team score after a made basket. `uncertain` = worth a second look.
export type ShotLog = {
  frame: number;
  t: number;
  player: string | null;
  team: string | null;
  made: boolean;
  points: number;
  three: boolean;
  reason: string;
  confidence: number | null;
  manual: boolean;
  recovered: boolean;
  uncertain: boolean;
  score: Record<string, number> | null;
};
export type ScoringMode = "standard" | "3x3";
export type Summary = {
  teams: { team: string; PTS: number; REB: number; AST: number }[];
  players: Card[];
  mvp: string | null;
  charts: string[];
  log: ShotLog[];
  scoring: ScoringMode;
  unassigned_pts: number;
};
export async function getSummary(id: string): Promise<Summary | null> {
  const r = await fetch(`${API}/games/${id}/summary`);
  return r.ok ? r.json() : null;
}
export const chartUrl = (id: string, name: string) => `${API}/games/${id}/chart/${name}`;

// Scoring corrections: each call re-counts the game on the server and returns the new summary.
async function send(method: string, path: string, body?: unknown): Promise<Summary> {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Could not update the score (${r.status})`);
  return r.json();
}
export const fixShot = (id: string, frame: number, fix: { made?: boolean; points?: number; player?: string }) =>
  send("POST", `/games/${id}/shots/${frame}`, fix);
export const addBasket = (id: string, b: { t: number; player: string; points?: number }) =>
  send("POST", `/games/${id}/baskets`, b);
export const undoCorrection = (id: string, kind: "shot" | "add", frame: number) =>
  send("DELETE", `/games/${id}/corrections/${kind}/${frame}`);
export const setScoring = (id: string, mode: ScoringMode) => send("PUT", `/games/${id}/scoring`, { mode });
