import React, { useMemo, useState } from "react";
import { View, Pressable, Image, Linking } from "react-native";
import { useApp } from "../state/AppContext";
import {
  Badge,
  Bar,
  Button,
  Card,
  Chip,
  Chips,
  Input,
  Row,
  Section,
  Segments,
  Slider,
  Stats,
  T,
} from "../components/ui";
import { TitleBadge } from "../components/PlayerCard";
import {
  nrBlank,
  nrPts,
  nrVal,
  nrMvp,
  nrScore,
  nrEval,
  nrNext,
  NR_TRACKS,
  SPEC,
  nrRankLabel,
} from "../state/progression";
import {
  nrAvg,
  nrMatch,
  nrStats,
  nrTierOf,
  nrUnlocks,
  nrExplain,
  NR_CFG,
  nrPlan,
} from "../state/mastery";
import players from "../data/players.json";
import { assets } from "../theme/assets";
import { accent } from "../theme/tokens";
import type { StatLine } from "../state/types";
const fields = [
  ["reb", "REB"],
  ["ast", "AST"],
  ["n1", "1PT made"],
  ["n2", "2PT made"],
  ["n3", "3PT made"],
  ["miss", "1-2PT miss"],
  ["miss3", "3PT miss"],
  ["pass", "Good passes"],
  ["foul", "Bad fouls"],
  ["pm", "+/-"],
] as const;
function GameLogger() {
  const { logGame, setLogging, colors, data } = useApp(),
    [minutes, setMinutes] = useState("20"),
    [teams, setTeams] = useState<StatLine[][]>(() => [
      Array.from({ length: 3 }, (_, i) => nrBlank(i ? "Teammate " + i : "You")),
      Array.from({ length: 3 }, (_, i) => nrBlank("Opponent " + (i + 1))),
    ]),
    [error, setError] = useState("");
  function field(t: number, i: number, k: keyof StatLine, v: string) {
    setTeams((a) =>
      a.map((team, ti) =>
        ti !== t
          ? team
          : team.map((p, pi) =>
              pi !== i
                ? p
                : {
                    ...p,
                    [k]:
                      k === "n"
                        ? v
                        : v === ""
                          ? k === "pm"
                            ? null
                            : 0
                          : Number(v),
                  },
            ),
      ),
    );
  }
  function save() {
    let err = "";
    teams.forEach((t) =>
      t.forEach((p) =>
        fields.forEach(([k]) => {
          const v = p[k];
          if (k === "pm") {
            if (v !== null && (!Number.isInteger(v) || v < -99 || v > 99))
              err = "+/- must be a whole number from -99 to 99.";
          } else if (
            !Number.isInteger(v) ||
            (v as number) < 0 ||
            (v as number) > 99
          )
            err = "Stats must be whole numbers from 0 to 99.";
        }),
      ),
    );
    if (!Number.isInteger(+minutes) || +minutes < 0 || +minutes > 120)
      err = "Minutes must be a whole number from 0 to 120.";
    if (err) {
      setError(err);
      return;
    }
    logGame({
      id: "u" + Date.now(),
      date: new Date().toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      title: "Logged game",
      min: +minutes,
      teams,
    });
  }
  return (
    <>
      <Card>
        <Row style={{ justifyContent: "space-between" }}>
          <T kind="h3">Log a game</T>
          <Badge>TEMPORARY</Badge>
        </Row>
        <T kind="muted" style={{ marginTop: 6, marginBottom: 10 }}>
          Game recording isn't connected yet, so enter the box score by hand.
          Log every player so MVP and titles can be worked out. Only your own
          line counts toward your titles and XP.
        </T>
        <Input
          label="Minutes you played"
          value={minutes}
          onChangeText={setMinutes}
          keyboardType="number-pad"
        />
      </Card>
      {teams.map((team, t) => (
        <View key={t}>
          <Section>
            <Row style={{ justifyContent: "space-between", width: "100%" }}>
              <T kind="h3">
                {t ? "Opponents" : "Your team"}{" "}
                <T kind="mono">{team.reduce((a, p) => a + nrPts(p), 0)} pts</T>
              </T>
              <Row style={{ gap: 8 }}>
                <Chip
                  onPress={() => {
                    if (team.length > 1)
                      setTeams((a) =>
                        a.map((x, j) => (j === t ? x.slice(0, -1) : x)),
                      );
                  }}
                >
                  −
                </Chip>
                <T kind="strong">{team.length}</T>
                <Chip
                  onPress={() => {
                    if (team.length < 8)
                      setTeams((a) =>
                        a.map((x, j) =>
                          j === t
                            ? [
                                ...x,
                                nrBlank(
                                  t
                                    ? "Opponent " + (x.length + 1)
                                    : "Teammate " + x.length,
                                ),
                              ]
                            : x,
                        ),
                      );
                  }}
                >
                  +
                </Chip>
              </Row>
            </Row>
          </Section>
          {team.map((p, i) => (
            <Card key={i} style={{ padding: 12 }}>
              <Row style={{ justifyContent: "space-between", gap: 8 }}>
                <View style={{ flex: 1 }}>
                  <Input
                    accessibilityLabel="Player name"
                    value={p.n}
                    editable={!(t === 0 && i === 0)}
                    maxLength={16}
                    onChangeText={(v) => field(t, i, "n", v)}
                    style={{ margin: 0 }}
                  />
                </View>
                <T kind="mono">
                  {nrVal(p)} value · {nrPts(p)} pts
                </T>
              </Row>
              <View
                className="flex-row flex-wrap gap-1.5"
                style={{ marginTop: 10 }}
              >
                {fields.map(([k, label]) => (
                  <View key={k} style={{ width: "23%", flexGrow: 1 }}>
                    <T
                      kind="mono"
                      numberOfLines={1}
                      style={{ fontSize: 8.5, marginBottom: 4 }}
                    >
                      {label}
                    </T>
                    <Input
                      accessibilityLabel={p.n + " " + label}
                      value={p[k] === null || p[k] === 0 ? "" : String(p[k])}
                      onChangeText={(v) => field(t, i, k, v)}
                      keyboardType={
                        k === "pm" ? "numbers-and-punctuation" : "number-pad"
                      }
                      placeholder={k === "pm" ? "opt." : "0"}
                      style={{
                        paddingHorizontal: 2,
                        paddingVertical: 8,
                        minHeight: 40,
                        fontSize: 14,
                        textAlign: "center",
                        marginBottom: 0,
                      }}
                    />
                  </View>
                ))}
              </View>
            </Card>
          ))}
        </View>
      ))}
      {!!error && <T style={{ color: "#ef4444", marginBottom: 10 }}>{error}</T>}
      <T kind="mono" style={{ marginVertical: 8 }}>
        Player Value = rebounds + 2 x assists + 3 x (1PT and 2PT baskets) + 4 x
        (3PT baskets). Highest value is MVP. +/- is optional and only used for
        The Anchor.
      </T>
      <Row style={{ gap: 8 }}>
        <Button style={{ flex: 1 }} onPress={() => setLogging(false)}>
          Cancel
        </Button>
        <Button primary style={{ flex: 2 }} onPress={save}>
          Save game
        </Button>
      </Row>
    </>
  );
}
function Sessions() {
  const { data, setData, setLogging, colors } = useApp(),
    [open, setOpen] = useState(""),
    [deleting, setDeleting] = useState("");
  return (
    <>
      <Button primary onPress={() => setLogging(true)}>
        Log a game
      </Button>
      <Section>Games</Section>
      {!data.games.length ? (
        <Card>
          <T kind="muted" style={{ textAlign: "center" }}>
            No games yet. Log your first game to earn PXP, find your MVP and
            start unlocking titles.
          </T>
        </Card>
      ) : (
        data.games
          .slice()
          .reverse()
          .map((g) => {
            const score = nrScore(g),
              mvp = nrMvp(g);
            return (
              <Card key={g.id}>
                <Pressable onPress={() => setOpen(open === g.id ? "" : g.id)}>
                  <Row style={{ justifyContent: "space-between" }}>
                    <View style={{ flex: 1 }}>
                      <T kind="strong">
                        {g.res === "W" ? "Win" : g.res === "L" ? "Loss" : "Tie"}{" "}
                        {score[0]}–{score[1]}
                      </T>
                      {mvp.includes("0:0") && <Badge>MVP</Badge>}
                      <T kind="mono">
                        {g.date} · {g.teams[0].length}v{g.teams[1].length} · +
                        {g.xp} PXP
                      </T>
                    </View>
                    <View>
                      <T style={{ fontSize: 11 }}>
                        <T kind="strong">{g.pts}</T> PTS ·{" "}
                        <T kind="strong">{g.ast}</T> AST ·{" "}
                        <T kind="strong">{g.reb}</T> REB
                      </T>
                      <T kind="mono">
                        Value {nrVal(g.teams[0][0])} · OVR {g.ovr}
                      </T>
                    </View>
                  </Row>
                </Pressable>
                {open === g.id && (
                  <View style={{ marginTop: 12 }}>
                    <T kind="hud">Box score</T>
                    {g.teams.map((team, t) => (
                      <View key={t}>
                        <T kind="mono" style={{ marginVertical: 8 }}>
                          {t ? "OPPONENTS" : "YOUR TEAM"}
                        </T>
                        {team.map((p, i) => (
                          <Row
                            key={i}
                            style={{
                              borderTopWidth: 1,
                              borderTopColor: colors.border,
                              paddingVertical: 5,
                            }}
                          >
                            <T
                              style={{
                                flex: 1,
                                fontSize: 12.5,
                                color: mvp.includes(`${t}:${i}`)
                                  ? accent
                                  : colors.text,
                              }}
                            >
                              {p.n}
                              {mvp.includes(`${t}:${i}`) ? "  MVP" : ""}
                            </T>
                            <T style={{ fontSize: 12.5 }}>
                              {nrPts(p)}p {p.ast}a {p.reb}r
                            </T>
                            <T kind="mono">{nrVal(p)}</T>
                          </Row>
                        ))}
                      </View>
                    ))}
                    <Chip
                      style={{
                        marginTop: 8,
                        alignSelf: "flex-start",
                        borderColor:
                          deleting === g.id ? "#ef4444" : colors.border,
                      }}
                      onPress={() => {
                        if (deleting !== g.id) {
                          setDeleting(g.id);
                          return;
                        }
                        setData((d) => ({
                          ...d,
                          games: d.games.filter((x) => x.id !== g.id),
                        }));
                        setDeleting("");
                      }}
                    >
                      {deleting === g.id
                        ? "Tap again to delete"
                        : "Delete game"}
                    </Chip>
                  </View>
                )}
              </Card>
            );
          })
      )}
    </>
  );
}
function Titles() {
  const { data, setData, title, overall, colors } = useApp(),
    ev = nrEval(data.games),
    [expanded, setExpanded] = useState("");
  const equip = (kind: string, key: string) =>
    setData((d) => ({
      ...d,
      equipped: kind === "auto" ? null : { kind, key },
    }));
  return (
    <>
      <Card>
        <Row style={{ gap: 12 }}>
          <TitleBadge name="allstar" size={54} locked={!data.games.length} />
          <View style={{ flex: 1 }}>
            <T kind="hud">Equipped title</T>
            <T kind="strong" style={{ fontSize: 18 }}>
              {title}
            </T>
            <T kind="mono">
              OVR {overall} · {data.games.reduce((a, g) => a + g.xp, 0)} PXP
              total
            </T>
          </View>
        </Row>
        <Row style={{ marginTop: 10, gap: 8 }}>
          <Chip
            selected={data.equipped?.kind === "rookie"}
            onPress={() => equip("rookie", "rookie")}
          >
            Rookie
          </Chip>
          <Chip selected={!data.equipped} onPress={() => equip("auto", "auto")}>
            Auto (best)
          </Chip>
        </Row>
      </Card>
      <Section>Ranked titles</Section>
      {NR_TRACKS.map((t) => {
        const rank = ev.ranks[t.k],
          next = nrNext(t, ev),
          on = data.equipped?.key === t.k;
        return (
          <Card key={t.k}>
            <Row style={{ gap: 12 }}>
              <TitleBadge name={t.k} rank={rank} locked={!rank} size={52} />
              <View style={{ flex: 1 }}>
                <T kind="strong" style={{ fontSize: 15 }}>
                  {t.name}
                </T>
                <T kind="mono">
                  {rank ? "Rank " + nrRankLabel(rank) : "Not earned yet"} ·{" "}
                  {t.blurb}
                </T>
              </View>
              {!!rank && (
                <Chip selected={on} onPress={() => equip("rank", t.k)}>
                  {on ? "Equipped" : "Equip"}
                </Chip>
              )}
            </Row>
            {next ? (
              <>
                <T kind="mono" style={{ marginTop: 10, marginBottom: 4 }}>
                  NEXT · RANK {nrRankLabel(next.rank)}
                </T>
                {next.req.map((q) => (
                  <View key={q.k}>
                    <Row
                      style={{ justifyContent: "space-between", marginTop: 4 }}
                    >
                      <T style={{ fontSize: 12 }}>{q.label}</T>
                      <T kind="mono">
                        {q.have} / {q.need}
                      </T>
                    </Row>
                    <Bar value={q.have / q.need} />
                  </View>
                ))}
              </>
            ) : (
              <T kind="mono" style={{ marginTop: 8 }}>
                Top rank reached.
              </T>
            )}
            <Pressable
              onPress={() => setExpanded(expanded === t.k ? "" : t.k)}
              style={{ marginTop: 10, minHeight: 44, justifyContent: "center" }}
            >
              <T kind="mono">{expanded === t.k ? "▾" : "▸"} All ranks</T>
            </Pressable>
            {expanded === t.k &&
              t.r.map((r, i) => (
                <Row
                  key={i}
                  style={{
                    paddingVertical: 4,
                    borderTopWidth: 1,
                    borderTopColor: colors.border,
                  }}
                >
                  <T
                    style={{
                      width: 18,
                      fontSize: 11.5,
                      color: rank >= i + 1 ? accent : colors.text,
                    }}
                  >
                    {nrRankLabel(i + 1)}
                  </T>
                  <T kind="muted" style={{ fontSize: 11.5, flex: 1 }}>
                    {Object.entries(r)
                      .map(([k, v]) => `${v} ${k}`)
                      .join(" + ")}
                  </T>
                </Row>
              ))}
          </Card>
        );
      })}
      <Section>Special titles</Section>
      <Card>
        {SPEC.map((s) => (
          <Row
            key={s.id}
            style={{
              paddingVertical: 10,
              borderTopWidth: 1,
              borderTopColor: colors.border,
            }}
          >
            <TitleBadge name={s.id} size={40} locked={!ev.spec[s.id]} />
            <View style={{ flex: 1 }}>
              <T kind="strong">{s.name}</T>
              <T kind="mono" style={{ fontSize: 10.5, lineHeight: 14.2 }}>
                {s.how}
              </T>
            </View>
            {!!ev.spec[s.id] && (
              <Chip
                selected={data.equipped?.key === s.id}
                onPress={() => equip("spec", s.id)}
              >
                Equip
              </Chip>
            )}
          </Row>
        ))}
      </Card>
      <Section>How MVP and PXP work</Section>
      <Card>
        <T kind="muted">
          Player Value = rebounds + 2 x assists + 3 x (1PT and 2PT baskets) + 4
          x (3PT baskets). The highest value in the game is MVP; ties go to
          points, then assists, then rebounds.
        </T>
        <T kind="muted" style={{ marginTop: 8 }}>
          Progression XP (PXP) per game: +20 for finishing, +20 for a win, +7
          per point, +5 per assist, +3 per rebound and −2 per bad foul. Every
          player starts at 55 OVR. The next point costs 100 PXP, then 110, 120
          and so on, 10 more each time, up to 99 OVR. Extra PXP carries over.
          This is temporary until game recording is connected.
        </T>
      </Card>
    </>
  );
}
const bankStats = nrStats(players);
function Mastery() {
  const { data, overall, colors } = useApp(),
    [tab, setTab] = useState("Overview"),
    [preview, setPreview] = useState<number | null>(null),
    [query, setQuery] = useState(""),
    [tierFilter, setTier] = useState("All"),
    [position, setPosition] = useState("All"),
    [era, setEra] = useState("All"),
    [status, setStatus] = useState("All"),
    [selected, setSelected] = useState(players[0].id),
    [flipped, setFlipped] = useState<string[]>([]);
  const avg = nrAvg(data.games),
    rating = preview ?? overall,
    tier = nrTierOf(rating),
    match = avg ? nrMatch(avg, rating, players, bankStats) : null,
    un = nrUnlocks(data.games, players, bankStats),
    p = players.find((p) => p.id === selected) || players[0],
    attrs = NR_CFG.attrs as {
      k: string;
      label: string;
      unit: string;
      pct?: boolean;
    }[];
  const list = players.filter(
    (p) =>
      p.name.toLowerCase().includes(query.toLowerCase()) &&
      (tierFilter === "All" || p.reqTier === tierFilter) &&
      (position === "All" || p.pos === position || p.pos2 === position) &&
      (era === "All" ||
        p.era === (era === "Current" ? "current" : "historical")) &&
      (status === "All" || (status === "Unlocked" ? !!un[p.id] : !un[p.id])),
  );
  const fmt = (v: number | null | undefined, pct = false) =>
    v == null ? "N/A" : v.toFixed(1) + (pct ? "%" : "");
  function compare(id: string) {
    setSelected(id);
    setTab("Compare");
  }
  return (
    <>
      <Chips
        options={["Overview", "Player bank", "Compare"]}
        value={tab}
        onChange={setTab}
      />
      {tab === "Overview" ? (
        <>
          <Card>
            <T kind="hud">Your NextRun rating</T>
            <Row>
              <T kind="h1" style={{ fontSize: 54, lineHeight: 60 }}>
                {Math.round(rating)}
              </T>
              <Badge>{tier?.k} TIER</Badge>
            </Row>
            <T kind="muted">{tier?.tier.blurb}</T>
            <T kind="mono" style={{ marginTop: 10 }}>
              Preview a rating{preview !== null ? " (not saved)" : ""}
            </T>
            <Slider
              min={55}
              max={99}
              value={rating}
              onChange={(v) => setPreview(Math.round(v))}
              label="Preview rating"
            />
            {preview !== null && (
              <Chip onPress={() => setPreview(null)}>Back to my rating</Chip>
            )}
          </Card>
          <Card>
            <Row style={{ justifyContent: "space-between" }}>
              <T kind="h3">Your five core stats</T>
              <T kind="mono">{avg ? avg.n + " games avg" : "no games"}</T>
            </Row>
            <View style={{ marginTop: 10 }}>
              <Stats
                columns={5}
                items={attrs.map((a) => [
                  avg ? fmt(avg[a.k], a.pct).replace(/\.0(%?)$/, "$1") : "—",
                  a.label,
                ])}
              />
            </View>
          </Card>
          <Card>
            <T kind="h3">Best NBA match</T>
            {match?.ok ? (
              <>
                <Row style={{ marginTop: 10, gap: 12 }}>
                  <Image
                    source={assets["player-" + match.best.id]}
                    style={{ width: 102, height: 90, borderRadius: 12 }}
                  />
                  <View style={{ flex: 1 }}>
                    <T kind="strong" style={{ fontSize: 19 }}>
                      {match.best.name}
                    </T>
                    <T kind="mono">Closeness {match.best.score}/100</T>
                  </View>
                </Row>
                <T kind="muted" style={{ marginVertical: 10 }}>
                  {nrExplain(match)}
                </T>
                <Row>
                  <Button
                    primary
                    style={{ flex: 1 }}
                    onPress={() => compare(match.best.id)}
                  >
                    Compare
                  </Button>
                  <Button
                    style={{ flex: 1 }}
                    onPress={() => setTab("Player bank")}
                  >
                    Browse bank
                  </Button>
                </Row>
                <T kind="hud" style={{ marginTop: 14, marginBottom: 6 }}>
                  Next closest
                </T>
                {match.list.slice(1, 5).map((x: any) => (
                  <Pressable
                    key={x.id}
                    onPress={() => compare(x.id)}
                    style={{ paddingVertical: 10 }}
                  >
                    <Row style={{ justifyContent: "space-between" }}>
                      <T>{x.name}</T>
                      <T kind="mono">{x.score}</T>
                    </Row>
                  </Pressable>
                ))}
              </>
            ) : (
              <>
                <T kind="muted" style={{ marginTop: 8, marginBottom: 10 }}>
                  {match?.reason || "Log a game to see your match."}
                </T>
                <Button onPress={() => setTab("Player bank")}>
                  Browse bank
                </Button>
              </>
            )}
          </Card>
          <Card>
            <Row style={{ justifyContent: "space-between" }}>
              <T kind="h3">Unlocked</T>
              <T kind="mono">
                {Object.keys(un).length} / {players.length}
              </T>
            </Row>
            <Bar value={Object.keys(un).length / players.length} />
            <View style={{ marginTop: 8 }}>
              <Stats
                columns={4}
                items={["D", "C", "B", "A"].map((t) => [
                  `${players.filter((p) => p.reqTier === t && un[p.id]).length}/${players.filter((p) => p.reqTier === t).length}`,
                  t + " TIER",
                ])}
              />
            </View>
            <T kind="muted" style={{ marginTop: 10 }}>
              A player unlocks when he is your closest match in a logged game
              while your rating is in his tier.
            </T>
          </Card>
          <T kind="mono">
            Closeness = 100 / (1 + weighted distance in standard deviations
            across the five stats). It ranks similarity, it is not a
            probability. NBA numbers are career per-game averages.
          </T>
        </>
      ) : tab === "Player bank" ? (
        <>
          <Input
            placeholder="Search players"
            value={query}
            onChangeText={setQuery}
          />
          {[
            ["Tier", ["All", "A", "B", "C", "D"], tierFilter, setTier],
            [
              "Position",
              ["All", "PG", "SG", "SF", "PF", "C"],
              position,
              setPosition,
            ],
            ["Era", ["All", "Current", "Legend"], era, setEra],
            ["Status", ["All", "Unlocked", "Locked"], status, setStatus],
          ].map(([label, opts, value, set]) => (
            <View key={label as string}>
              <T kind="hud" style={{ marginTop: 8, marginBottom: 4 }}>
                {label as string}
              </T>
              <Chips
                options={opts as string[]}
                value={value as string}
                onChange={set as (s: string) => void}
              />
            </View>
          ))}
          <T kind="mono" style={{ marginTop: 10, marginBottom: 6 }}>
            {Object.keys(un).length} of {players.length} unlocked. Tap a card to
            flip it.
          </T>
          <View className="flex-row flex-wrap gap-2.5">
            {list.map((player) => (
              <Pressable
                key={player.id}
                onPress={() =>
                  setFlipped((f) =>
                    f.includes(player.id)
                      ? f.filter((x) => x !== player.id)
                      : [...f, player.id],
                  )
                }
                style={{
                  width: "48%",
                  flexGrow: 1,
                  borderWidth: 1,
                  borderColor: un[player.id] ? accent : colors.border,
                  borderRadius: 16,
                  overflow: "hidden",
                  backgroundColor: colors.surface,
                  minHeight: 272,
                }}
              >
                {flipped.includes(player.id) ? (
                  <View style={{ padding: 10, gap: 6 }}>
                    <T kind="strong">{player.name}</T>
                    <T kind="hud">Unlock target</T>
                    <T kind="muted" style={{ fontSize: 11 }}>
                      {player.archetypes.join(" · ")}
                    </T>
                    {attrs.map((a) => (
                      <Row
                        key={a.k}
                        style={{ justifyContent: "space-between" }}
                      >
                        <T kind="mono">{a.label}</T>
                        <T kind="mono">{fmt((player as any)[a.k], a.pct)}</T>
                      </Row>
                    ))}
                    <Chip onPress={() => compare(player.id)}>Compare</Chip>
                  </View>
                ) : (
                  <>
                    <Image
                      source={
                        assets[
                          "player-" +
                            player.id +
                            (un[player.id] ? "" : "-locked")
                        ]
                      }
                      style={{ width: "100%", height: 150 }}
                    />
                    <View
                      style={{
                        position: "absolute",
                        left: 8,
                        top: 8,
                        backgroundColor: "#0a0a0c",
                        borderWidth: 1,
                        borderColor: accent,
                        borderRadius: 6,
                        paddingHorizontal: 7,
                        paddingVertical: 2,
                      }}
                    >
                      <T kind="mono" style={{ color: accent }}>
                        {player.reqTier}
                      </T>
                    </View>
                    <View
                      style={{
                        position: "absolute",
                        right: 6,
                        top: 8,
                        backgroundColor: un[player.id]
                          ? accent
                          : "rgba(60,60,66,.9)",
                        borderRadius: 6,
                        padding: 3,
                      }}
                    >
                      <T kind="mono" style={{ fontSize: 8.5, color: "#ddd" }}>
                        {un[player.id] ? "UNLOCKED" : "LOCKED"}
                      </T>
                    </View>
                    <T
                      kind="strong"
                      style={{
                        fontFamily: "Montserrat-800",
                        paddingHorizontal: 10,
                        paddingTop: 8,
                        lineHeight: 16.1,
                      }}
                    >
                      {player.name}
                    </T>
                    <T
                      kind="mono"
                      style={{
                        fontSize: 10.5,
                        paddingHorizontal: 10,
                        paddingVertical: 3,
                      }}
                    >
                      {player.pos} · {player.hin}
                    </T>
                    <Row
                      style={{
                        gap: 2,
                        paddingHorizontal: 6,
                        paddingVertical: 6,
                        marginTop: "auto",
                      }}
                    >
                      {attrs.map((a) => (
                        <View
                          key={a.k}
                          style={{ flex: 1, alignItems: "center" }}
                        >
                          <T
                            kind="mono"
                            style={{ fontSize: 11, color: colors.text }}
                          >
                            {fmt((player as any)[a.k]).replace(".0", "")}
                          </T>
                          <T kind="mono" style={{ fontSize: 8 }}>
                            {a.label}
                          </T>
                        </View>
                      ))}
                    </Row>
                  </>
                )}
              </Pressable>
            ))}
          </View>
          {!list.length && (
            <T kind="muted" style={{ textAlign: "center", padding: 24 }}>
              No players match these filters.
            </T>
          )}
        </>
      ) : (
        <>
          <T kind="mono" style={{ marginBottom: 6 }}>
            Compare with
          </T>
          <Chips
            options={players.map((x) => x.name)}
            value={p.name}
            onChange={(name) =>
              setSelected(players.find((x) => x.name === name)!.id)
            }
          />
          <Card style={{ marginTop: 12 }}>
            <Row style={{ gap: 12 }}>
              <Image
                source={assets["player-" + p.id + (un[p.id] ? "" : "-locked")]}
                style={{ width: 102, height: 90, borderRadius: 12 }}
              />
              <View style={{ flex: 1 }}>
                <T kind="strong" style={{ fontSize: 19 }}>
                  {p.name}
                </T>
                <T kind="mono">
                  {p.reqTier} tier · {p.pos} · {p.hin}
                </T>
                <T kind="mono">
                  {p.era === "current" ? "Current era" : "Historical"} ·{" "}
                  {un[p.id] ? "Unlocked" : "Locked"}
                </T>
              </View>
            </Row>
            <T kind="muted" style={{ marginTop: 8 }}>
              {p.archetypes.join(" · ")}. Career per game, {p.span}.
            </T>
            <Pressable onPress={() => Linking.openURL(p.src)}>
              <T style={{ color: accent, fontSize: 13 }}>{p.srcName}</T>
            </Pressable>
            {!!p.note && <T kind="mono">{p.note}</T>}
          </Card>
          <Card>
            {!avg && (
              <T kind="muted">No games logged yet, so your side is empty.</T>
            )}
            <T kind="mono" style={{ marginBottom: 6 }}>
              YOU: average of {avg?.n || 0} logged games ·{" "}
              {p.name.toUpperCase()}: career average
            </T>
            {attrs.map((a) => {
              const u = avg?.[a.k],
                n = (p as any)[a.k],
                mx = Math.max(u || 0, n || 0) * 1.12 || 1;
              return (
                <View key={a.k} style={{ marginBottom: 14 }}>
                  <Row style={{ justifyContent: "space-between" }}>
                    <T kind="strong">{a.label}</T>
                    <T kind="mono">{a.unit}</T>
                  </Row>
                  {[
                    ["You", u],
                    [p.name.split(" ").at(-1), n],
                  ].map(([label, value], i) => (
                    <Row key={label} style={{ gap: 8, marginTop: 5 }}>
                      <T kind="mono" style={{ width: 54 }}>
                        {label}
                      </T>
                      <View style={{ flex: 1 }}>
                        <Bar value={value == null ? 0 : value / mx} />
                      </View>
                      <T kind="mono" style={{ width: 54, textAlign: "right" }}>
                        {fmt(value, a.pct)}
                      </T>
                    </Row>
                  ))}
                  <T kind="mono" style={{ marginTop: 4 }}>
                    {u == null
                      ? "You have no attempts logged."
                      : n == null
                        ? "Unavailable for this player."
                        : `You are ${u >= n ? "ahead" : "behind"} by ${Math.abs(u - n).toFixed(1)}${a.pct ? " pts" : ""}`}
                  </T>
                </View>
              );
            })}
          </Card>
        </>
      )}
    </>
  );
}
export function History() {
  const { historyTab, setHistoryTab, logging } = useApp();
  return (
    <>
      <T kind="hud">Track record</T>
      <T kind="h2">History</T>
      <View style={{ marginVertical: 12 }}>
        <Segments
          options={["Sessions", "Mastery", "Titles"]}
          value={historyTab}
          onChange={setHistoryTab}
        />
      </View>
      {historyTab === "Sessions" ? (
        logging ? (
          <GameLogger />
        ) : (
          <Sessions />
        )
      ) : historyTab === "Mastery" ? (
        <Mastery />
      ) : (
        <Titles />
      )}
    </>
  );
}
