import React, { useState } from "react";
import { View, Pressable, Modal, ScrollView } from "react-native";
import { useApp, questBank, dayKey } from "../state/AppContext";
import {
  Art,
  Badge,
  Bar,
  Button,
  Card,
  Float,
  Icon,
  IconButton,
  Logo,
  Row,
  Section,
  T,
} from "../components/ui";
import { accent } from "../theme/tokens";
import { nrEval, nrNext, NR_TRACKS } from "../state/progression";
import { TitleBadge } from "../components/PlayerCard";
export function LevelCard() {
  const { overall, level, title, data, setLogging, setHistoryTab, go } =
    useApp();
  return (
    <Card>
      <Row style={{ gap: 12 }}>
        <TitleBadge name="allstar" locked={!data.games.length} size={46} />
        <View style={{ flex: 1 }}>
          <T kind="hud">Overall · {overall} OVR</T>
          <T kind="strong" style={{ fontSize: 17, marginTop: 2 }}>
            {title}
          </T>
          <Bar value={level.pct} />
          <T kind="mono" style={{ marginTop: 3 }}>
            {overall === 99
              ? "Max overall (99)"
              : `${level.cur} / ${level.need} PXP to OVR ${overall + 1}`}
          </T>
        </View>
      </Row>
      {!data.games.length && (
        <T kind="muted" style={{ marginTop: 10 }}>
          You are a new player. Log your first game to start earning PXP and
          titles.
        </T>
      )}
      <Button
        primary
        style={{ marginTop: 10, marginBottom: 0 }}
        onPress={() => {
          setHistoryTab("Sessions");
          setLogging(true);
          go("history");
        }}
      >
        <Icon name="stat" size={18} color="#fff" />
        <T style={{ color: "#fff", fontFamily: "Inter-600", fontSize: 15 }}>
          Log a game
        </T>
      </Button>
    </Card>
  );
}
export function ProgressCard() {
  const { data } = useApp(),
    last = data.games.at(-1);
  if (!last)
    return (
      <Card>
        <Row style={{ justifyContent: "space-between" }}>
          <T kind="h3">Your progress</T>
          <T kind="mono">no games yet</T>
        </Row>
        <T kind="muted" style={{ marginTop: 10 }}>
          Your shooting, latest game and win record show up here after your
          first logged game. Game recording is not connected yet, so games are
          logged by hand.
        </T>
      </Card>
    );
  const totals = data.games.reduce(
      (a, g) => ({ m: a.m + g.fgm, a: a.a + g.fga }),
      { m: 0, a: 0 },
    ),
    pct = totals.a ? Math.round((totals.m / totals.a) * 100) : 0;
  return (
    <Card>
      <Row style={{ justifyContent: "space-between" }}>
        <T kind="h3">Your progress</T>
        <T kind="mono">{last.date} · latest game</T>
      </Row>
      <Row style={{ marginTop: 12, gap: 18 }}>
        <View
          style={{
            width: 112,
            height: 112,
            borderWidth: 9,
            borderColor: accent,
            borderRadius: 112,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <T kind="h1">{pct}%</T>
        </View>
        <View style={{ flex: 1 }}>
          <T kind="mono">LATEST GAME</T>
          {[
            ["PTS", last.pts],
            ["AST", last.ast],
            ["REB", last.reb],
          ].map(([k, v]) => (
            <Row
              key={k}
              style={{ justifyContent: "space-between", paddingVertical: 7 }}
            >
              <T kind="mono">{k}</T>
              <T kind="h2">{v}</T>
            </Row>
          ))}
        </View>
      </Row>
      <Row style={{ justifyContent: "space-between", marginTop: 12 }}>
        <T kind="hud">Shooting {pct}%</T>
        <T style={{ fontSize: 13, color: accent }}>
          {data.games.length} games ·{" "}
          {data.games.filter((g) => g.res === "W").length} W
        </T>
      </Row>
    </Card>
  );
}
function DailyQuest() {
  const { data, setData, completeQuest, go } = useApp(),
    q = data.quest,
    n = q.done.length,
    all = n === 3;
  const now = new Date(),
    end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1),
    m = Math.floor((+end - +now) / 60000);
  return (
    <Card>
      <Row style={{ justifyContent: "space-between" }}>
        <View>
          <T kind="hud">Daily quest</T>
          <T kind="h3" style={{ marginTop: 2 }}>
            {all ? "All clear" : "Today’s missions"}
          </T>
        </View>
        <View>
          <Row>
            <Icon name="flame" size={16} color={accent} />
            <T kind="strong">{data.streak}</T>
            <T kind="mono">days</T>
          </Row>
          <T kind="mono" style={{ marginTop: 3 }}>
            Resets in {Math.floor(m / 60)}h {String(m % 60).padStart(2, "0")}m
          </T>
        </View>
      </Row>
      <Bar value={n / 3} />
      {q.ids.map((id) => {
        const it = questBank.find((x) => x[0] === id)!,
          done = q.done.includes(id),
          auto = it.length > 4;
        return (
          <Row
            key={id}
            style={{
              paddingVertical: 12,
              borderBottomWidth: 1,
              borderBottomColor: "rgba(128,128,128,.15)",
              gap: 9,
            }}
          >
            <View
              style={{
                width: 22,
                height: 22,
                borderRadius: 7,
                borderWidth: 1,
                borderColor: done ? accent : "#dcdde0",
                backgroundColor: done ? accent : "transparent",
                alignItems: "center",
              }}
            >
              <T style={{ color: "#fff" }}>{done ? "✓" : ""}</T>
            </View>
            <View style={{ flex: 1 }}>
              <T kind="strong" style={{ fontSize: 12.5 }}>
                {it[1]}
              </T>
              <T kind="muted" style={{ fontSize: 10.5, lineHeight: 15 }}>
                {it[2]}
              </T>
            </View>
            <T kind="mono" style={{ color: accent }}>
              +{it[3]}
            </T>
            {!done && (
              <Pressable
                onPress={() => (auto ? go(it[4] as any) : completeQuest(id))}
                style={{
                  minHeight: 44,
                  paddingHorizontal: 10,
                  justifyContent: "center",
                  borderWidth: 1,
                  borderColor: "rgba(128,128,128,.2)",
                  borderRadius: 20,
                }}
              >
                <T style={{ fontSize: 11 }}>{auto ? "Go" : "Done"}</T>
              </Pressable>
            )}
          </Row>
        );
      })}
      <Row style={{ marginTop: 12, justifyContent: "space-between" }}>
        <T kind="mono">QUEST POINTS · {data.questXp}</T>
        {all ? (
          !q.claimed ? (
            <Button
              primary
              style={{ width: "auto", margin: 0, padding: 10 }}
              onPress={() =>
                setData((d) => ({
                  ...d,
                  quest: { ...d.quest, claimed: true },
                  questXp: d.questXp + 40,
                  streak:
                    d.lastClaim ===
                    new Date(Date.now() - 86400000).toLocaleDateString("en-CA")
                      ? d.streak + 1
                      : 1,
                  lastClaim: dayKey(),
                }))
              }
            >
              Claim +40 points
            </Button>
          ) : (
            <Badge>BONUS CLAIMED</Badge>
          )
        ) : (
          <T kind="mono">{n}/3 complete</T>
        )}
      </Row>
    </Card>
  );
}
export function Goals() {
  const { data, go, setHistoryTab } = useApp(),
    ev = nrEval(data.games);
  return (
    <>
      <Section>Title goals</Section>
      <Card>
        {NR_TRACKS.slice(0, 3).map((t) => {
          const next = nrNext(t, ev);
          if (!next) return null;
          const pct =
            next.req.reduce((a, r) => a + r.have / r.need, 0) / next.req.length;
          return (
            <View key={t.k} style={{ marginBottom: 14 }}>
              <Row style={{ justifyContent: "space-between" }}>
                <T style={{ fontSize: 13 }}>
                  {t.name} · Rank {next.rank}
                </T>
                <T kind="mono">{Math.round(pct * 100)}%</T>
              </Row>
              <Bar value={pct} />
              <T kind="mono" style={{ marginTop: 3 }}>
                {next.req
                  .map((r) => `${r.have}/${r.need} ${r.label}`)
                  .join(" · ")}
              </T>
            </View>
          );
        })}
        <Button
          style={{
            alignSelf: "flex-start",
            marginBottom: 0,
            paddingVertical: 10,
          }}
          onPress={() => {
            setHistoryTab("Titles");
            go("history");
          }}
        >
          See all titles
        </Button>
      </Card>
    </>
  );
}
export function Home() {
  const { data, setData, go, colors, setHistoryTab } = useApp(),
    [notices, setNotices] = useState(false);
  return (
    <>
      <Row style={{ justifyContent: "space-between" }}>
        <Logo />
        <Row style={{ gap: 8 }}>
          <IconButton
            name="bulb"
            label="Switch light or dark mode"
            onPress={() =>
              setData((d) => ({
                ...d,
                theme: d.theme === "light" ? "dark" : "light",
              }))
            }
          />
          <IconButton
            name="bell"
            label="Notifications"
            badge={data.notices.filter((n) => !n.read).length}
            onPress={() => setNotices(true)}
          />
        </Row>
      </Row>
      <T kind="hud" style={{ marginTop: 18 }}>
        {data.games.length ? "Welcome back" : "Welcome"}
      </T>
      <T kind="h1" style={{ marginTop: 2 }}>
        {data.handle || "Player"}
      </T>
      <T kind="muted" style={{ marginBottom: 14 }}>
        {data.games.length
          ? "Keep pushing."
          : "Day one. Everyone starts as a Rookie."}
      </T>
      <View
        style={{
          height: 292,
          borderRadius: 26,
          overflow: "hidden",
          borderWidth: 1,
          borderColor: colors.border,
          paddingVertical: 22,
          paddingHorizontal: 20,
        }}
      >
        <Art
          name="arena"
          style={{
            position: "absolute",
            inset: 0,
            width: undefined,
            height: undefined,
          }}
        />
        <Art
          name="hero"
          style={{
            position: "absolute",
            right: -6,
            bottom: 0,
            width: 237,
            height: "100%",
          }}
          resizeMode="contain"
        />
        <T kind="hud">The Locker Room</T>
        <T
          style={{
            fontFamily: "Montserrat-600",
            fontSize: 25,
            lineHeight: 32.5,
            letterSpacing: 4,
            marginTop: 12,
          }}
        >
          ANALYZE{"\n"}IMPROVE{"\n"}COMPETE
        </T>
        <View
          style={{
            width: 32,
            height: 4,
            borderRadius: 2,
            marginTop: 16,
            backgroundColor: accent,
          }}
        />
      </View>
      <Pressable
        onPress={() => go("camera")}
        accessibilityRole="button"
        style={{
          marginTop: -56,
          marginHorizontal: 12,
          padding: 14,
          borderRadius: 22,
          borderWidth: 1,
          borderColor: colors.border,
          backgroundColor:
            data.theme === "light"
              ? "rgba(255,255,255,.90)"
              : "rgba(13,13,15,.90)",
        }}
      >
        <Row style={{ gap: 14 }}>
          <View
            style={{
              width: 52,
              height: 52,
              borderRadius: 52,
              backgroundColor: accent,
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name="arr" color="#fff" size={24} />
          </View>
          <View style={{ flex: 1 }}>
            <T kind="strong" style={{ fontSize: 13, letterSpacing: 1.82 }}>
              START SESSION
            </T>
            <T
              kind="muted"
              style={{ fontSize: 12, lineHeight: 16.2, marginTop: 3 }}
            >
              Track your performance with AI powered analytics.
            </T>
          </View>
        </Row>
      </Pressable>
      <Row style={{ gap: 8, marginVertical: 12 }}>
        {[
          ["cam", "Camera", "camera"],
          ["stat", "Stats", "history"],
          ["fr", "Community", "club"],
          ["me", "Profile", "profile"],
        ].map(([i, t, r]) => (
          <Pressable
            key={t}
            onPress={() => {
              if (r === "history") setHistoryTab("Sessions");
              go(r as any);
            }}
            style={{
              flex: 1,
              paddingTop: 13,
              paddingBottom: 11,
              borderRadius: 18,
              borderWidth: 1,
              borderColor: colors.border,
              backgroundColor: colors.surface,
              alignItems: "center",
              gap: 7,
            }}
          >
            <Float>
              <Icon name={i} color={accent} />
            </Float>
            <T style={{ fontSize: 11, fontFamily: "Inter-500" }}>{t}</T>
          </Pressable>
        ))}
      </Row>
      <LevelCard />
      <DailyQuest />
      <ProgressCard />
      <Goals />
      <Modal
        visible={notices}
        transparent
        animationType="slide"
        onRequestClose={() => setNotices(false)}
      >
        <Pressable
          style={{
            flex: 1,
            backgroundColor: "rgba(0,0,0,.55)",
            justifyContent: "flex-end",
          }}
          onPress={() => setNotices(false)}
        >
          <Pressable
            style={{
              maxHeight: "78%",
              backgroundColor: colors.surface,
              padding: 18,
              borderTopLeftRadius: 26,
              borderTopRightRadius: 26,
            }}
            onPress={() => {}}
          >
            <Row style={{ justifyContent: "space-between", marginBottom: 14 }}>
              <T kind="h2">Notifications</T>
              <Button onPress={() => setNotices(false)}>✕</Button>
            </Row>
            <ScrollView>
              {data.notices.length ? (
                data.notices.map((n) => (
                  <Pressable
                    key={n.id}
                    onPress={() => {
                      setData((d) => ({
                        ...d,
                        notices: d.notices.map((x) =>
                          x.id === n.id ? { ...x, read: true } : x,
                        ),
                      }));
                      setNotices(false);
                      go(n.route);
                    }}
                  >
                    <Card>
                      <T kind="strong">{n.title}</T>
                      <T kind="muted">{n.body}</T>
                    </Card>
                  </Pressable>
                ))
              ) : (
                <T kind="muted">You’re all caught up.</T>
              )}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}
