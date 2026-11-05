import React, { useEffect, useState } from "react";
import { Image, Pressable, Text, TextInput, View } from "react-native";
import { Card, Label } from "./ui";
import {
  addBasket,
  Card as PlayerCard,
  chartUrl,
  fixShot,
  getSummary,
  ScoringMode,
  setScoring,
  ShotLog,
  Summary,
  undoCorrection,
} from "../lib/api";

const INK = "#0B1220",
  PANEL = "#111A2E",
  LINE = "#1E2A44",
  GOLD = "#FBBF24",
  TEAM = ["#F28B30", "#3D8BFD", "#34D399", "#F472B6"];
const teamColor = (team: string | null, teams: string[]) =>
  TEAM[Math.max(0, teams.indexOf(team ?? "")) % TEAM.length];

function Count({ to, size = 56, color = "#fff" }: { to: number; size?: number; color?: string }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let n = 0;
    const step = Math.max(1, Math.ceil(to / 18));
    const timer = setInterval(() => {
      n = Math.min(to, n + step);
      setV(n);
      if (n >= to) clearInterval(timer);
    }, 45);
    return () => clearInterval(timer);
  }, [to]);
  return <Text style={{ color, fontSize: size, fontWeight: "800", fontVariant: ["tabular-nums"] }}>{v}</Text>;
}

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", marginTop: 6 }}>
      <Text style={{ width: 34, color: "#94A3B8", fontSize: 11, fontWeight: "700" }}>{label}</Text>
      <View style={{ flex: 1, height: 8, borderRadius: 4, backgroundColor: LINE, overflow: "hidden" }}>
        <View style={{ width: `${Math.max(value ? 8 : 0, (100 * value) / Math.max(1, max))}%`, height: 8, backgroundColor: color, borderRadius: 4 }} />
      </View>
      <Text style={{ width: 30, textAlign: "right", color: "#fff", fontSize: 14, fontWeight: "800" }}>{value}</Text>
    </View>
  );
}

function Player({ c, max, teams }: { c: PlayerCard; max: { PTS: number; REB: number; AST: number }; teams: string[] }) {
  const [open, setOpen] = useState(false),
    col = teamColor(c.team, teams),
    init = c.player.replace(/^Player\s*/, "P");
  return (
    <Pressable onPress={() => setOpen(!open)} style={{ backgroundColor: PANEL, borderRadius: 16, padding: 12, marginTop: 10, borderWidth: 1, borderColor: c.rank === 1 ? GOLD : LINE }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <View style={{ width: 42, height: 42, borderRadius: 21, backgroundColor: col, alignItems: "center", justifyContent: "center" }}>
          <Text style={{ color: "#fff", fontWeight: "800", fontSize: 15 }}>{init}</Text>
        </View>
        <View style={{ flex: 1, marginLeft: 10 }}>
          <Text style={{ color: "#fff", fontWeight: "800", fontSize: 16 }}>{c.player}</Text>
          <Text style={{ color: "#94A3B8", fontSize: 11 }}>
            {c.team ? `Team ${c.team} · ` : ""}LVL {c.level} · #{c.rank}
          </Text>
        </View>
        <View style={{ alignItems: "flex-end" }}>
          <Text style={{ color: GOLD, fontWeight: "800", fontSize: 22 }}>{c.RATING.toFixed(1)}</Text>
          <Text style={{ color: "#94A3B8", fontSize: 9, fontWeight: "700" }}>RATING</Text>
        </View>
      </View>
      {c.badges.length > 0 && (
        <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 8 }}>
          {c.badges.map((b) => (
            <View key={b} style={{ backgroundColor: b === "MVP" ? GOLD : LINE, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 999, marginRight: 6, marginBottom: 4 }}>
              <Text style={{ color: b === "MVP" ? INK : "#E2E8F0", fontSize: 10, fontWeight: "800" }}>{b === "MVP" ? "★ MVP" : b}</Text>
            </View>
          ))}
        </View>
      )}
      <Bar label="PTS" value={c.PTS} max={max.PTS} color={col} />
      <Bar label="REB" value={c.REB} max={max.REB} color="#A78BFA" />
      <Bar label="AST" value={c.AST} max={max.AST} color="#22D3EE" />
      <View style={{ height: 6, borderRadius: 3, backgroundColor: LINE, marginTop: 10, overflow: "hidden" }}>
        <View style={{ width: `${((c.xp % 50) / 50) * 100}%`, height: 6, backgroundColor: GOLD }} />
      </View>
      {open && (
        <View style={{ marginTop: 10 }}>
          <Text style={{ color: "#94A3B8", fontSize: 11 }}>
            FG {c.FGM}/{c.FGA} · 3PT {c["3PM"]}/{c["3PA"]} · STL {c.STL} · TOV {c.TOV}
          </Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 6 }}>
            {c.shots.length === 0 && <Text style={{ color: "#64748B", fontSize: 11 }}>No shots detected</Text>}
            {c.shots.map((s, i) => (
              <View key={i} style={{ backgroundColor: s.made ? "#16A34A" : "#B91C1C", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, marginRight: 5, marginBottom: 5 }}>
                <Text style={{ color: "#fff", fontSize: 10, fontWeight: "700" }}>
                  {s.t.toFixed(0)}s {s.made ? `+${s.points}` : "miss"}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}
    </Pressable>
  );
}

const clock = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

function Chip({ label, on, onPress, color = GOLD, disabled }: { label: string; on?: boolean; onPress: () => void; color?: string; disabled?: boolean }) {
  return (
    <Pressable
      disabled={disabled}
      onPress={onPress}
      style={{ backgroundColor: on ? color : LINE, opacity: disabled ? 0.5 : 1, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, marginRight: 6, marginTop: 6 }}
    >
      <Text style={{ color: on ? INK : "#E2E8F0", fontSize: 11, fontWeight: "800" }}>{label}</Text>
    </Pressable>
  );
}

// "+2 ✓" / "MISS" row of the scoring log. Tap it to fix what the AI decided.
function LogRow({ e, names, teams, busy, onFix, onUndo }: {
  e: ShotLog;
  names: string[];
  teams: string[];
  busy: boolean;
  onFix: (fix: { made?: boolean; points?: number; player?: string }) => void;
  onUndo: () => void;
}) {
  const [open, setOpen] = useState(false),
    col = e.team ? teamColor(e.team, teams) : "#64748B",
    run = teams.length ? teams.map((t) => `${t} ${e.score?.[t] ?? 0}`).join(" – ") : "";
  return (
    <Pressable onPress={() => setOpen(!open)} style={{ borderTopWidth: 1, borderTopColor: LINE, paddingVertical: 10 }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ width: 40, color: "#64748B", fontSize: 12, fontWeight: "700", fontVariant: ["tabular-nums"] }}>{clock(e.t)}</Text>
        <View style={{ width: 4, height: 28, borderRadius: 2, backgroundColor: col, marginRight: 8 }} />
        <View style={{ flex: 1 }}>
          <Text style={{ color: "#fff", fontSize: 14, fontWeight: "800" }}>{e.player ?? "Who scored?"}</Text>
          <Text style={{ color: "#94A3B8", fontSize: 11 }} numberOfLines={open ? 3 : 1}>
            {e.made ? run : "missed shot"}
            {e.manual ? " · edited by you" : e.recovered ? " · found at the rim" : ""}
          </Text>
        </View>
        {e.uncertain && (
          <View style={{ backgroundColor: "#78350F", borderRadius: 999, paddingHorizontal: 7, paddingVertical: 2, marginRight: 8 }}>
            <Text style={{ color: "#FDE68A", fontSize: 9, fontWeight: "800" }}>CHECK</Text>
          </View>
        )}
        <Text style={{ color: e.made ? "#34D399" : "#F87171", fontSize: 16, fontWeight: "800", minWidth: 44, textAlign: "right" }}>
          {e.made ? `+${e.points}` : "MISS"}
        </Text>
      </View>
      {open && (
        <View style={{ marginTop: 8 }}>
          <View style={{ flexDirection: "row", flexWrap: "wrap" }}>
            <Chip disabled={busy} on color={e.made ? "#B91C1C" : "#16A34A"} label={e.made ? "✗ Not a basket" : "✓ Count it as a basket"} onPress={() => onFix({ made: !e.made })} />
            {e.manual && <Chip disabled={busy} label="Undo my change" onPress={onUndo} />}
          </View>
          {e.made && (
            <View style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "center", marginTop: 2 }}>
              <Text style={{ color: "#94A3B8", fontSize: 11, marginTop: 6, marginRight: 6 }}>Points</Text>
              {[1, 2, 3].map((n) => (
                <Chip key={n} disabled={busy} on={e.points === n} label={`${n}`} onPress={() => onFix({ points: n })} />
              ))}
            </View>
          )}
          <View style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "center" }}>
            <Text style={{ color: "#94A3B8", fontSize: 11, marginTop: 6, marginRight: 6 }}>Credit to</Text>
            {names.map((n) => (
              <Chip key={n} disabled={busy} on={e.player === n} label={n} onPress={() => onFix({ player: n })} />
            ))}
          </View>
        </View>
      )}
    </Pressable>
  );
}

// A basket the AI never saw at all: when, who, how many points.
function AddBasket({ names, busy, defaultPts, onAdd }: { names: string[]; busy: boolean; defaultPts: number; onAdd: (t: number, player: string, pts: number) => void }) {
  const [open, setOpen] = useState(false),
    [time, setTime] = useState(""),
    [who, setWho] = useState<string | null>(null),
    [pts, setPts] = useState(defaultPts);
  const secs = (() => {
      const m = time.trim().match(/^(\d+):(\d{1,2})$/);
      return m ? Number(m[1]) * 60 + Number(m[2]) : Number(time);
    })(),
    ok = !!who && time.trim() !== "" && Number.isFinite(secs) && secs >= 0;
  if (!open)
    return (
      <Pressable onPress={() => setOpen(true)} style={{ borderTopWidth: 1, borderTopColor: LINE, paddingTop: 12, marginTop: 2 }}>
        <Text style={{ color: GOLD, fontSize: 13, fontWeight: "800" }}>＋ A basket is missing</Text>
      </Pressable>
    );
  return (
    <View style={{ borderTopWidth: 1, borderTopColor: LINE, paddingTop: 12, marginTop: 2 }}>
      <Text style={{ color: "#fff", fontSize: 13, fontWeight: "800" }}>Add a basket</Text>
      <View style={{ flexDirection: "row", alignItems: "center", marginTop: 8 }}>
        <Text style={{ color: "#94A3B8", fontSize: 11, marginRight: 8 }}>Time in the video (seconds or m:ss)</Text>
        <TextInput
          value={time}
          onChangeText={setTime}
          placeholder="12"
          placeholderTextColor="#475569"
          keyboardType="numbers-and-punctuation"
          style={{ color: "#fff", backgroundColor: LINE, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, minWidth: 70, fontSize: 14 }}
        />
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap" }}>
        {names.map((n) => (
          <Chip key={n} on={who === n} label={n} onPress={() => setWho(n)} />
        ))}
      </View>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ color: "#94A3B8", fontSize: 11, marginTop: 6, marginRight: 6 }}>Points</Text>
        {[1, 2, 3].map((n) => (
          <Chip key={n} on={pts === n} label={`${n}`} onPress={() => setPts(n)} />
        ))}
      </View>
      <View style={{ flexDirection: "row", marginTop: 10 }}>
        <Chip on color="#16A34A" disabled={!ok || busy} label="Add basket" onPress={() => { onAdd(secs, who!, pts); setOpen(false); setTime(""); setWho(null); }} />
        <Chip label="Cancel" onPress={() => setOpen(false)} />
      </View>
    </View>
  );
}

// Final score, MVP, a card for every player (points, rebounds, assists, rating, level, badges, shot log) and the charts.
export function GameDashboard({ id }: { id: string }) {
  const [sum, setSum] = useState<Summary | null>(null),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setSum(null);
    getSummary(id).then(setSum).catch(() => {});
  }, [id]);
  // every correction re-counts the game on the server and sends back the new numbers
  const apply = async (p: Promise<Summary>) => {
    setBusy(true);
    setErr(null);
    try {
      setSum(await p);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };
  if (!sum) return null;
  const names = sum.teams.map((t) => t.team).filter((t) => t !== "?"),
    teams = names.length ? sum.teams.filter((t) => t.team !== "?") : sum.teams,
    max = {
      PTS: Math.max(1, ...sum.players.map((p) => p.PTS)),
      REB: Math.max(1, ...sum.players.map((p) => p.REB)),
      AST: Math.max(1, ...sum.players.map((p) => p.AST)),
    },
    mvp = sum.players.find((p) => p.player === sum.mvp),
    who = sum.players.map((p) => p.player),
    check = sum.log.filter((l) => l.uncertain).length;
  return (
    <View style={{ marginTop: 12 }}>
      <View style={{ backgroundColor: INK, borderRadius: 20, padding: 16 }}>
        <Text style={{ color: "#64748B", fontSize: 11, fontWeight: "800", letterSpacing: 2, textAlign: "center" }}>FINAL · AI-TRACKED</Text>
        <View style={{ flexDirection: "row", justifyContent: "space-around", marginTop: 10 }}>
          {teams.slice(0, 2).map((t) => (
            <View key={t.team} style={{ alignItems: "center" }}>
              <View style={{ width: 34, height: 4, borderRadius: 2, backgroundColor: teamColor(t.team, names), marginBottom: 6 }} />
              <Count to={t.PTS} />
              <Text style={{ color: "#94A3B8", fontSize: 12, fontWeight: "700" }}>Team {t.team}</Text>
              <Text style={{ color: "#64748B", fontSize: 10 }}>{t.REB} REB · {t.AST} AST</Text>
            </View>
          ))}
        </View>
        <View style={{ flexDirection: "row", justifyContent: "center", alignItems: "center", marginTop: 12 }}>
          <Chip disabled={busy} on={sum.scoring === "standard"} label="2s & 3s" onPress={() => apply(setScoring(id, "standard" as ScoringMode))} />
          <Chip disabled={busy} on={sum.scoring === "3x3"} label="3x3 · 1s & 2s" onPress={() => apply(setScoring(id, "3x3" as ScoringMode))} />
        </View>
        {sum.unassigned_pts > 0 && (
          <Text style={{ color: "#FDE68A", fontSize: 11, textAlign: "center", marginTop: 8 }}>
            +{sum.unassigned_pts} not counted yet: a basket went in but nobody was seen with the ball. Pick who scored in the scoring log.
          </Text>
        )}
      </View>
      {mvp && (
        <View style={{ backgroundColor: INK, borderRadius: 16, padding: 12, marginTop: 10, borderWidth: 1.5, borderColor: GOLD, flexDirection: "row", alignItems: "center" }}>
          <Text style={{ fontSize: 28 }}>🏆</Text>
          <View style={{ marginLeft: 10, flex: 1 }}>
            <Text style={{ color: GOLD, fontSize: 10, fontWeight: "800", letterSpacing: 1.5 }}>PLAYER OF THE GAME</Text>
            <Text style={{ color: "#fff", fontSize: 18, fontWeight: "800" }}>{mvp.player}</Text>
            <Text style={{ color: "#94A3B8", fontSize: 12 }}>{mvp.PTS} PTS · {mvp.REB} REB · {mvp.AST} AST</Text>
          </View>
          <Text style={{ color: GOLD, fontSize: 26, fontWeight: "800" }}>{mvp.RATING.toFixed(1)}</Text>
        </View>
      )}
      <View style={{ backgroundColor: PANEL, borderRadius: 16, padding: 14, marginTop: 14 }}>
        <View style={{ flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" }}>
          <Text style={{ color: "#fff", fontSize: 16, fontWeight: "800" }}>Scoring log</Text>
          <Text style={{ color: "#64748B", fontSize: 11 }}>
            {sum.log.filter((l) => l.made).length} baskets · {sum.log.length} shots{check ? ` · ${check} to check` : ""}
          </Text>
        </View>
        <Text style={{ color: "#64748B", fontSize: 11, marginTop: 2, marginBottom: 6 }}>
          Every shot the AI saw. Tap one to count it, remove it, or change who scored.
        </Text>
        {sum.log.length === 0 && <Text style={{ color: "#94A3B8", fontSize: 12, paddingVertical: 8 }}>No shots detected in this video.</Text>}
        {sum.log.map((l) => (
          <LogRow
            key={`${l.frame}-${l.manual ? "m" : "a"}`}
            e={l}
            names={who}
            teams={names}
            busy={busy}
            onFix={(fix) => apply(fixShot(id, l.frame, fix))}
            onUndo={() => apply(undoCorrection(id, "shot", l.frame))}
          />
        ))}
        <AddBasket names={who} busy={busy} defaultPts={sum.scoring === "3x3" ? 1 : 2} onAdd={(t, player, points) => apply(addBasket(id, { t, player, points }))} />
        {!!err && <Text style={{ color: "#F87171", fontSize: 12, marginTop: 8 }}>{err}</Text>}
      </View>
      <Label kind="h3" style={{ marginTop: 14 }}>Players</Label>
      {sum.players.map((c) => (
        <Player key={c.player} c={c} max={max} teams={names} />
      ))}
      {sum.charts.includes("shot_chart") && (
        <Card style={{ marginTop: 14 }}>
          <Label kind="h3">Shot chart</Label>
          <Image source={{ uri: chartUrl(id, "shot_chart") }} style={{ width: "100%", aspectRatio: 1.5, marginTop: 8, borderRadius: 12 }} resizeMode="contain" />
        </Card>
      )}
      {sum.charts.includes("pass_network") && (
        <Card style={{ marginTop: 12 }}>
          <Label kind="h3">Passing network</Label>
          <Image source={{ uri: chartUrl(id, "pass_network") }} style={{ width: "100%", aspectRatio: 1.5, marginTop: 8, borderRadius: 12 }} resizeMode="contain" />
        </Card>
      )}
    </View>
  );
}
