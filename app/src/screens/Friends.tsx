import React, { useState } from "react";
import { View } from "react-native";
import { useApp } from "../state/AppState";
import {
  Avatar,
  Button,
  Card,
  Chips,
  Icon,
  Input,
  Label,
  Progress,
  Row,
  Scene,
} from "../components/ui";
import { useTheme } from "../theme/theme";
const friends = [
  ["PlayerOne", "In a game · 2h", "green"],
  ["Hooper23", "At practice · 34m", "orange"],
  ["BallsLife", "Offline · 3h", "offline"],
  ["CourtVision", "In club · 1h", "green"],
  ["BucketsOnly", "Offline · 5h", "offline"],
  ["DunkMaster", "Busy · 45m", "red"],
];
export function Friends() {
  const { s, patch } = useApp(),
    t = useTheme(),
    [query, search] = useState(""),
    [message, setMessage] = useState("");
  const list = friends.filter(
    (f) =>
      (s.filter === "All" ||
        (s.filter === "Online" && f[2] !== "offline") ||
        (s.filter === "Offline" && f[2] === "offline")) &&
      f[0].toLowerCase().includes(query.toLowerCase()),
  );
  function send() {
    if (message.trim()) {
      patch({ chat: [...s.chat, { me: true, text: message.trim() }] });
      setMessage("");
    }
  }
  return (
    <>
      <Scene
        name="shoes"
        style={{
          borderRadius: 22,
          paddingTop: 34,
          paddingHorizontal: 18,
          paddingBottom: 16,
          marginBottom: 12,
          borderWidth: 1,
          borderColor: t.border,
          boxShadow: t.shadow,
        }}
      >
        <Label kind="hud">Squad</Label>
        <Label kind="h2" style={{ marginTop: 2 }}>
          The Crew
        </Label>
        <Label kind="mono">4 online now</Label>
      </Scene>
      <View>
        <Input
          accessibilityLabel="Search friends, clubs, handles"
          placeholder="Search friends, clubs, handles"
          value={query}
          onChangeText={search}
          style={{ paddingLeft: 42 }}
        />
        <View
          pointerEvents="none"
          style={{ position: "absolute", left: 14, top: 14 }}
        >
          <Icon name="search" size={18} color={t.muted} />
        </View>
      </View>
      <Chips
        values={["Active", "Messages", "Rivalry"]}
        value={s.friendsTab}
        onChange={(friendsTab) => patch({ friendsTab })}
      />
      {s.friendsTab === "Active" ? (
        <>
          <Chips
            compact
            values={["All", "Online", "Offline", "Requests"]}
            value={s.filter}
            onChange={(filter) => patch({ filter })}
          />
          {list.length ? (
            list.map(([name, status, state]) => (
              <Card key={name} style={{ paddingVertical: 11 }}>
                <Row style={{ gap: 12 }}>
                  <Avatar />
                  <View style={{ flex: 1 }}>
                    <Label style={{ fontFamily: "Inter_600" }}>{name}</Label>
                    <Label kind="mono">{status}</Label>
                  </View>
                  <View
                    style={{
                      width: 9,
                      height: 9,
                      borderRadius: 9,
                      backgroundColor:
                        state === "green"
                          ? "#22c55e"
                          : state === "orange"
                            ? t.accent
                            : state === "red"
                              ? "#ef4444"
                              : t.muted,
                      boxShadow:
                        state === "offline"
                          ? undefined
                          : `0 0 8px ${state === "green" ? "#22c55e" : state === "red" ? "#ef4444" : t.accent}`,
                    }}
                  />
                </Row>
              </Card>
            ))
          ) : (
            <Label
              kind="muted"
              style={{ textAlign: "center", marginVertical: 22 }}
            >
              {s.filter === "Requests"
                ? "No pending requests."
                : "Nobody here yet."}
            </Label>
          )}
        </>
      ) : s.friendsTab === "Messages" ? (
        <Card>
          <Row
            style={{
              paddingBottom: 10,
              marginBottom: 10,
              borderBottomWidth: 1,
              borderColor: t.border,
            }}
          >
            <Avatar size={38} style={{ borderRadius: 12 }} />
            <View>
              <Label style={{ fontFamily: "Inter_600" }}>Hooper23</Label>
              <Label kind="mono">At practice · 34m</Label>
            </View>
          </Row>
          {s.chat.map((m, i) => (
            <View
              key={i}
              style={{
                maxWidth: "78%",
                paddingVertical: 9,
                paddingHorizontal: 12,
                borderRadius: 16,
                backgroundColor: m.me ? t.accent : t.surface2,
                marginBottom: 8,
                alignSelf: m.me ? "flex-end" : "flex-start",
                boxShadow: m.me ? t.glow : undefined,
              }}
            >
              <Label style={{ fontSize: 13, color: m.me ? t.on : t.text }}>
                {m.text}
              </Label>
            </View>
          ))}
          <Row>
            <Input
              accessibilityLabel="Message Hooper23"
              placeholder="Message Hooper23"
              value={message}
              onChangeText={setMessage}
              onSubmitEditing={send}
              style={{ flex: 1, marginBottom: 0 }}
            />
            <Button
              primary
              onPress={send}
              style={{ width: 70, marginBottom: 0 }}
            >
              Send
            </Button>
          </Row>
        </Card>
      ) : (
        <Card>
          <Label kind="hud" style={{ textAlign: "center" }}>
            Head to head
          </Label>
          <Row between style={{ marginVertical: 14 }}>
            <View style={{ alignItems: "center", gap: 6 }}>
              <Avatar size={54} />
              <Label>You</Label>
            </View>
            <Label
              style={{
                fontFamily: "Montserrat_800Italic",
                fontSize: 42,
                letterSpacing: -0.84,
              }}
            >
              <Label
                style={{
                  fontFamily: "Montserrat_800Italic",
                  fontSize: 42,
                  color: t.accent,
                }}
              >
                7
              </Label>{" "}
              – 4
            </Label>
            <View style={{ alignItems: "center", gap: 6 }}>
              <Avatar
                size={54}
                style={{ backgroundColor: t.surface2, borderColor: t.border }}
              />
              <Label>Hooper23</Label>
            </View>
          </Row>
          <Progress value={64} />
          <Label kind="muted" style={{ textAlign: "center", marginTop: 10 }}>
            You lead by 3. Next matchup: Saturday.
          </Label>
        </Card>
      )}
    </>
  );
}
