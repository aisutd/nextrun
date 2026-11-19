import React from "react";
import { Text, View } from "react-native";
import { LiveEvent, LiveFrame, LiveGame } from "../lib/api";

// Shared by the browser (LiveCamera.web.tsx) and phone (LiveCamera.tsx) live cameras.
export const BONES: [number, number][] = [
  [5, 6],
  [5, 7],
  [7, 9],
  [6, 8],
  [8, 10],
  [5, 11],
  [6, 12],
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
];
export const ZONE_COLOR: Record<string, string> = { "3PT": "#22c55e", "2PT": "#3b82f6", CLOSE: "#eab308" };

export function DetectChips({ last, accent }: { last: LiveFrame | null; accent: string }) {
  const holder = last?.players.find((p) => p.has_ball);
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
      {[
        `Players ${last?.players.length ?? 0}`,
        `Ball ${last?.ball ? "✓" : "–"}`,
        `Hoops ${last?.rims.length ?? 0}`,
        `Court ${last?.court?.usable ? `✓ ${Math.round(last.court.conf * 100)}%` : last ? "searching…" : "–"}`,
        holder ? `Ball: #${holder.track_id}${holder.zone ? ` (${holder.zone})` : ""}` : null,
      ]
        .filter(Boolean)
        .map((x) => (
          <Text
            key={x!}
            style={{
              fontSize: 11,
              fontFamily: "Inter_600",
              color: accent,
              borderWidth: 1,
              borderColor: accent,
              borderRadius: 999,
              paddingHorizontal: 8,
              paddingVertical: 3,
            }}
          >
            {x}
          </Text>
        ))}
    </View>
  );
}

export const who = (p: string | null | undefined) => (!p ? "unknown" : p.startsWith("track:") ? `#${p.slice(6)}` : p);

export function LiveStats({ game, accent }: { game: LiveGame | null; accent: string }) {
  const T = game?.totals;
  const tiles: [string, string | number][] = [
    ["PTS", T?.points ?? 0],
    ["FG", T ? `${T.makes}/${T.shots}` : "0/0"],
    ["MISS", T?.misses ?? 0],
    ["REB", T?.rebounds ?? 0],
    ["AST", T?.assists ?? 0],
    ["POSS", T?.possessions ?? 0],
  ];
  const box = {
    borderWidth: 1,
    borderColor: "rgba(127,127,127,.25)",
    borderRadius: 16,
    padding: 12,
    marginTop: 10,
  } as const;
  return (
    <View>
      <View style={[box, { flexDirection: "row", justifyContent: "space-between" }]}>
        {tiles.map(([k, v]) => (
          <View key={k} style={{ alignItems: "center", flex: 1 }}>
            <Text style={{ fontSize: 20, fontFamily: "Inter_600", color: k === "PTS" ? accent : "#888" }}>
              <Text style={{ color: k === "PTS" ? accent : undefined }}>{v}</Text>
            </Text>
            <Text style={{ fontSize: 10, color: "#888", letterSpacing: 1 }}>{k}</Text>
          </View>
        ))}
      </View>
      <View style={box}>
        <Text style={{ fontSize: 11, color: "#888", letterSpacing: 1, marginBottom: 6 }}>LIVE PLAY-BY-PLAY</Text>
        {!game?.events.length ? (
          <Text style={{ fontSize: 12, color: "#888" }}>
            {game ? "Waiting for the first shot…" : "Starting game tracking…"}
          </Text>
        ) : (
          game.events.slice(0, 6).map((e, i) => (
            <View key={`${e.type}-${e.t}-${i}`} style={{ flexDirection: "row", gap: 8, paddingVertical: 3 }}>
              <Text style={{ fontSize: 11, color: "#888", width: 42, fontVariant: ["tabular-nums"] }}>{fmt(e.t)}</Text>
              <Text style={{ fontSize: 12, flex: 1, color: e.type === "shot" && e.made ? accent : "#888" }}>
                {describe(e)}
              </Text>
            </View>
          ))
        )}
      </View>
      {!!game?.players.some((p) => p.PTS || p.REB || p.AST || p.FGA) && (
        <View style={box}>
          <View style={{ flexDirection: "row", marginBottom: 4 }}>
            {["PLAYER", "PTS", "FG", "REB", "AST"].map((h, i) => (
              <Text
                key={h}
                style={{
                  fontSize: 10,
                  color: "#888",
                  letterSpacing: 1,
                  flex: i ? 1 : 2,
                  textAlign: i ? "center" : "left",
                }}
              >
                {h}
              </Text>
            ))}
          </View>
          {game.players
            .filter((p) => p.PTS || p.REB || p.AST || p.FGA)
            .slice(0, 8)
            .map((p) => (
              <View key={p.player} style={{ flexDirection: "row", paddingVertical: 3 }}>
                {[who(p.player), p.PTS, `${p.FGM}/${p.FGA}`, p.REB, p.AST].map((v, i) => (
                  <Text
                    key={i}
                    style={{
                      fontSize: 12,
                      color: i === 1 ? accent : "#888",
                      flex: i ? 1 : 2,
                      textAlign: i ? "center" : "left",
                      fontFamily: i === 1 ? "Inter_600" : undefined,
                    }}
                  >
                    {v}
                  </Text>
                ))}
              </View>
            ))}
        </View>
      )}
      <Text style={{ fontSize: 10, color: "#888", marginTop: 6 }}>
        Live stats are an estimate. Stop recording to run the full analysis.
      </Text>
    </View>
  );
}

const fmt = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

function describe(e: LiveEvent): string {
  const p = who(e.player);
  switch (e.type) {
    case "shot":
      return e.made
        ? `${p} scores ${e.points}${e.three ? " (3PT)" : ""}${e.dunk ? " · dunk" : ""}`
        : `${p} misses${e.three ? " a 3" : ""}`;
    case "rebound":
      return `${p} ${e.offensive ? "offensive" : "defensive"} rebound`;
    case "assist":
      return `${p} assist${e.to ? ` to ${who(e.to)}` : ""}`;
    case "steal":
      return `${p} steal`;
    case "turnover":
      return `${p} turnover`;
  }
}
