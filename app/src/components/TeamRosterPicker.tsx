import React, { useEffect, useMemo, useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import { Button, Card, Label, Row } from "./ui";
import { useTheme } from "../theme/theme";
import { getTeamRoster, RosterPlayer, RosterTeam, rosterThumbUrl, saveRosterTeams } from "../lib/api";

const INK = "#0B1220",
  LINE = "#1E2A44",
  TEAM_COLOR: Record<string, string> = { A: "#22D3EE", B: "#FB923C" },
  OUT = "#475569";

// Tap order on a player card: Team A -> Team B -> not playing -> Team A ...
const NEXT: Record<string, RosterTeam> = { A: "B", B: null, null: "A" };

const PICK = "#FACC15";

function PlayerCard({ id, p, team, onPress, merged = 0, picking, picked }: {
  id: string; p: RosterPlayer; team: RosterTeam; onPress: () => void; merged?: number; picking?: boolean; picked?: boolean;
}) {
  const color = picked ? PICK : team ? TEAM_COLOR[team] : OUT;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={
        picking
          ? picked ? `${p.name}, keeping this one. Tap their duplicates.` : `${p.name}. Tap to ${picked === false ? "merge into the player you picked" : "keep this player"}.`
          : `${p.name}, ${team ? `Team ${team}` : "not playing"}. Tap to change.`
      }
      onPress={onPress}
      style={{ width: "31%", minWidth: 96, marginBottom: 10, borderRadius: 12, borderWidth: picked ? 3 : 2, borderColor: color, backgroundColor: INK, overflow: "hidden", opacity: team || picking ? 1 : 0.6 }}
    >
      <Image source={{ uri: rosterThumbUrl(id, p) }} style={{ width: "100%", aspectRatio: 3 / 4, backgroundColor: "#070B12" }} resizeMode="cover" />
      <View style={{ position: "absolute", top: 6, left: 6, backgroundColor: color, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2 }}>
        <Text style={{ color: team ? "#0B1220" : "#F1F5F9", fontSize: 10, fontWeight: "900" }}>{team ? `TEAM ${team}` : "OUT"}</Text>
      </View>
      {merged > 0 && (
        <View style={{ position: "absolute", top: 6, right: 6, backgroundColor: PICK, borderRadius: 999, paddingHorizontal: 7, paddingVertical: 2 }}>
          <Text style={{ color: "#0B1220", fontSize: 10, fontWeight: "900" }}>+{merged}</Text>
        </View>
      )}
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
  const t = useTheme();
  const [players, setPlayers] = useState<RosterPlayer[] | null>(null),
    [teams, setTeamsState] = useState<Record<number, RosterTeam>>({}),
    [showOff, setShowOff] = useState(false),
    [busy, setBusy] = useState(false),
    [msg, setMsg] = useState(""),
    // Fix duplicates: the tracker can lose a player and pick them up as someone new. mergedInto[duplicate key] = kept key
    [mergedInto, setMergedInto] = useState<Record<number, number>>({}),
    [fixing, setFixing] = useState(false),
    [keep, setKeep] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setPlayers(null);
    getTeamRoster(id)
      .then((r) => {
        if (cancelled) return;
        setPlayers(r.players);
        setTeamsState(Object.fromEntries(r.players.map((p) => [p.key, p.team === "A" || p.team === "B" ? p.team : null])));
        setMergedInto({});
        setFixing(false);
        setKeep(null);
      })
      .catch((e) => !cancelled && setMsg((e as Error).message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  // a merged duplicate is not a person of its own: hidden from the grid and the counts, saved as the kept player
  const people = useMemo(() => (players ?? []).filter((p) => mergedInto[p.key] == null), [players, mergedInto]);
  const onCourt = useMemo(() => people.filter((p) => p.on_court !== false), [people]),
    offCourt = useMemo(() => people.filter((p) => p.on_court === false), [people]);
  const byKey = useMemo(() => Object.fromEntries((players ?? []).map((p) => [p.key, p])), [players]);
  const mergedCount = (key: number) => Object.values(mergedInto).filter((k) => k === key).length;
  const count = (t: RosterTeam) => people.filter((p) => teams[p.key] === t).length;
  const nA = count("A"),
    nB = count("B");

  function setAll(list: RosterPlayer[], t: RosterTeam) {
    setTeamsState((cur) => ({ ...cur, ...Object.fromEntries(list.map((p) => [p.key, t])) }));
  }

  function tap(p: RosterPlayer) {
    if (!fixing) return setTeamsState((c) => ({ ...c, [p.key]: NEXT[String(c[p.key] ?? null)] }));
    if (keep == null || keep === p.key) return setKeep(keep === p.key ? null : p.key);
    // fold p (and anything already merged into p) into the kept player
    setMergedInto((cur) => {
      const next = { ...cur, [p.key]: keep };
      for (const [k, v] of Object.entries(next)) if (v === p.key) next[Number(k)] = keep;
      return next;
    });
  }

  function unmerge(key: number) {
    setMergedInto((cur) => {
      const next = { ...cur };
      delete next[key];
      return next;
    });
  }

  async function save() {
    if (!players) return;
    setBusy(true);
    setMsg("");
    try {
      // a duplicate is saved under the kept player's name and team, so all their tracks count as one person
      await saveRosterTeams(
        id,
        players.map((p) => {
          const k = mergedInto[p.key];
          const owner = k != null ? byKey[k] : p;
          return { player: { ...p, name: owner.name }, team: teams[owner.key] ?? null };
        }),
      );
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
        {fixing
          ? keep == null
            ? "Fix duplicates: tap the player to keep."
            : `Now tap every other card of ${byKey[keep]?.name ?? "them"} to merge it in. Tap them again when done.`
          : "Everyone the AI tracked on the court during the whole video. Tap a player to switch Team A → Team B → not playing."}
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
              <PlayerCard key={p.key} id={id} p={p} team={teams[p.key] ?? null} onPress={() => tap(p)} merged={mergedCount(p.key)}
                picking={fixing} picked={fixing && keep != null ? keep === p.key : undefined} />
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
                      <PlayerCard key={p.key} id={id} p={p} team={teams[p.key] ?? null} onPress={() => tap(p)} merged={mergedCount(p.key)}
                        picking={fixing} picked={fixing && keep != null ? keep === p.key : undefined} />
                    ))}
                  </View>
                  <Button onPress={() => setAll(offCourt, null)} style={{ borderRadius: 999, paddingVertical: 8 }} textStyle={{ fontSize: 12 }}>Mark all off-court as not playing</Button>
                </>
              )}
            </>
          )}
          <Button
            onPress={() => {
              setFixing((v) => !v);
              setKeep(null);
            }}
            style={{ borderRadius: 999, paddingVertical: 8, marginTop: 4, borderColor: fixing ? PICK : undefined }}
            textStyle={{ fontSize: 12, color: fixing ? PICK : undefined }}
          >
            {fixing ? "Done fixing duplicates" : "Same person twice? Fix duplicates"}
          </Button>
          {Object.keys(mergedInto).length > 0 && (
            <View style={{ marginTop: 6 }}>
              {Object.entries(mergedInto).map(([dup, k]) => (
                <Row between key={dup} style={{ paddingVertical: 4 }}>
                  <Text style={{ color: t.muted, fontSize: 12, flex: 1 }}>
                    {byKey[Number(dup)]?.name} is the same person as <Text style={{ color: t.text, fontWeight: "700" }}>{byKey[k]?.name}</Text>
                  </Text>
                  <Pressable accessibilityRole="button" accessibilityLabel={`Undo merging ${byKey[Number(dup)]?.name}`} onPress={() => unmerge(Number(dup))}>
                    <Text style={{ color: PICK, fontSize: 12, fontWeight: "800" }}>Undo</Text>
                  </Pressable>
                </Row>
              ))}
            </View>
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
