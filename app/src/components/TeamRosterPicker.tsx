import React, { useEffect, useMemo, useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { Button, Card, Label, Row } from "./ui";
import { getTeamRoster, RosterPlayer, RosterTeam, rosterThumbUrl, saveRosterTeams } from "../lib/api";

const INK = "#0B1220",
  LINE = "#1E2A44",
  TEAM_COLOR: Record<string, string> = { A: "#22D3EE", B: "#FB923C" },
  OUT = "#475569";

// Tap order on a player card: Team A -> Team B -> not playing -> Team A ...
const NEXT: Record<string, RosterTeam> = { A: "B", B: null, null: "A" };

function PlayerCard({ id, p, team, onPress }: { id: string; p: RosterPlayer; team: RosterTeam; onPress: () => void }) {
  const color = team ? TEAM_COLOR[team] : OUT;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${p.name}, ${team ? `Team ${team}` : "not playing"}. Tap to change.`}
      onPress={onPress}
      style={{ width: "31%", minWidth: 96, marginBottom: 10, borderRadius: 12, borderWidth: 2, borderColor: color, backgroundColor: INK, overflow: "hidden", opacity: team ? 1 : 0.6 }}
    >
      <Image source={{ uri: rosterThumbUrl(id, p) }} style={{ width: "100%", aspectRatio: 3 / 4, backgroundColor: "#070B12" }} resizeMode="cover" />
      <View style={{ position: "absolute", top: 6, left: 6, backgroundColor: color, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2 }}>
        <Text style={{ color: team ? "#0B1220" : "#F1F5F9", fontSize: 10, fontWeight: "900" }}>{team ? `TEAM ${team}` : "OUT"}</Text>
      </View>
      <View style={{ padding: 6 }}>
        <Text style={{ color: "#F1F5F9", fontSize: 12, fontWeight: "800" }} numberOfLines={1}>{p.name}</Text>
        <Text style={{ color: "#64748B", fontSize: 10 }}>on screen {p.seen_s}s</Text>
      </View>
    </Pressable>
  );
}

// Assign every person the tracker saw anywhere in the video (not just in one frame) to Team A, Team B or "not
// playing". On-court people come pre-filled with the jersey-colour guess; off-court people start as not playing.
export function TeamRosterPicker({ id, disabled, onSaved }: { id: string; disabled?: boolean; onSaved: () => void }) {
  const [players, setPlayers] = useState<RosterPlayer[] | null>(null),
    [teams, setTeamsState] = useState<Record<number, RosterTeam>>({}),
    [showOff, setShowOff] = useState(false),
    [busy, setBusy] = useState(false),
    [msg, setMsg] = useState("");

  useEffect(() => {
    let cancelled = false;
    setPlayers(null);
    getTeamRoster(id)
      .then((r) => {
        if (cancelled) return;
        setPlayers(r.players);
        setTeamsState(Object.fromEntries(r.players.map((p) => [p.key, p.team === "A" || p.team === "B" ? p.team : null])));
      })
      .catch((e) => !cancelled && setMsg((e as Error).message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const onCourt = useMemo(() => (players ?? []).filter((p) => p.on_court !== false), [players]),
    offCourt = useMemo(() => (players ?? []).filter((p) => p.on_court === false), [players]);
  const count = (t: RosterTeam) => (players ?? []).filter((p) => teams[p.key] === t).length;
  const nA = count("A"),
    nB = count("B");

  function setAll(list: RosterPlayer[], t: RosterTeam) {
    setTeamsState((cur) => ({ ...cur, ...Object.fromEntries(list.map((p) => [p.key, t])) }));
  }

  async function save() {
    if (!players) return;
    setBusy(true);
    setMsg("");
    try {
      await saveRosterTeams(id, players.map((p) => ({ player: p, team: teams[p.key] ?? null })));
      setMsg("Teams saved. Updating stats and the annotated video…");
      onSaved();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card style={{ marginTop: 12 }}>
      <Label kind="h3">Set up teams</Label>
      <Label kind="muted" style={{ marginTop: 4 }}>
        Everyone the AI tracked on the court during the whole video. Tap a player to switch Team A → Team B → not playing.
      </Label>
      {!players ? (
        <Label kind="muted" style={{ marginTop: 12 }}>{msg || "Finding everyone in the video…"}</Label>
      ) : (
        <>
          <Row between style={{ marginTop: 12, marginBottom: 8 }}>
            <Text style={{ color: TEAM_COLOR.A, fontWeight: "800" }}>Team A · {nA}</Text>
            <Text style={{ color: TEAM_COLOR.B, fontWeight: "800" }}>Team B · {nB}</Text>
            <Text style={{ color: "#94A3B8", fontWeight: "700" }}>Out · {count(null)}</Text>
          </Row>
          <Label kind="muted" style={{ marginBottom: 8 }}>On the court · {onCourt.length}</Label>
          <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" }}>
            {onCourt.map((p) => (
              <PlayerCard key={p.key} id={id} p={p} team={teams[p.key] ?? null} onPress={() => setTeamsState((c) => ({ ...c, [p.key]: NEXT[String(c[p.key] ?? null)] }))} />
            ))}
          </View>
          {offCourt.length > 0 && (
            <>
              <Button onPress={() => setShowOff((v) => !v)} style={{ borderRadius: 999, paddingVertical: 8, marginTop: 4 }} textStyle={{ fontSize: 12 }}>
                {showOff ? "Hide" : "Show"} people off the court · {offCourt.length}
              </Button>
              {showOff && (
                <>
                  <Label kind="muted" style={{ marginTop: 8, marginBottom: 8 }}>Spectators and people at the edge. Tap one if they actually played.</Label>
                  <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" }}>
                    {offCourt.map((p) => (
                      <PlayerCard key={p.key} id={id} p={p} team={teams[p.key] ?? null} onPress={() => setTeamsState((c) => ({ ...c, [p.key]: NEXT[String(c[p.key] ?? null)] }))} />
                    ))}
                  </View>
                  <Button onPress={() => setAll(offCourt, null)} style={{ borderRadius: 999, paddingVertical: 8 }} textStyle={{ fontSize: 12 }}>Mark all off-court as not playing</Button>
                </>
              )}
            </>
          )}
          {msg ? <Label kind="muted" style={{ marginTop: 8 }}>{msg}</Label> : null}
          {(nA === 0 || nB === 0) && <Label kind="muted" style={{ marginTop: 8 }}>Put at least one player on each team.</Label>}
          <View style={{ height: 1, backgroundColor: LINE, marginVertical: 10 }} />
          <Button onPress={save} disabled={busy || disabled || nA === 0 || nB === 0} style={{ borderRadius: 999, paddingVertical: 10, marginBottom: 0 }} textStyle={{ fontSize: 12 }}>
            {busy ? "Saving…" : disabled ? "Wait for processing to finish…" : `Save teams and score · ${nA} vs ${nB}`}
          </Button>
        </>
      )}
    </Card>
  );
}
