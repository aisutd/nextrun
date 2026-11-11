import React, { useState } from "react";
import { View, ScrollView, Pressable, Image } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useApp, heightLabel, weightLabel } from "../state/AppContext";
import { keepImage } from "../state/storage";
import {
  Art,
  Button,
  Card,
  Chips,
  Chip,
  IconButton,
  Input,
  Row,
  Section,
  Stats,
  T,
  Toggle,
} from "../components/ui";
import { PlayerCard, TitleBadge } from "../components/PlayerCard";
import { nrEval, NR_TRACKS } from "../state/progression";
import { accent } from "../theme/tokens";
import design from "../data/design.json";
import type { CardOptions } from "../state/types";
export function Profile() {
  const { data, go, setEditing, setHistoryTab, title } = useApp(),
    ev = nrEval(data.games),
    [flipped, setFlipped] = useState(false);
  return (
    <>
      <Row style={{ justifyContent: "space-between" }}>
        <View>
          <T kind="hud">You</T>
          <T kind="h2">Player card</T>
        </View>
        <IconButton
          name="gear"
          label="Settings"
          onPress={() => go("settings")}
        />
      </Row>
      <View
        style={{
          paddingTop: 18,
          paddingBottom: 4,
          marginTop: 14,
          marginBottom: 10,
          borderRadius: 24,
          overflow: "hidden",
        }}
      >
        <Art
          name="net"
          style={{
            position: "absolute",
            inset: 0,
            width: undefined,
            height: undefined,
          }}
        />
        <PlayerCard
          options={data.card.useCustom ? data.card : undefined}
          flipped={flipped}
          onFlip={() => setFlipped((f) => !f)}
        />
      </View>
      <Button onPress={() => setFlipped((f) => !f)}>Flip card</Button>
      <Button onPress={() => go("history")}>History &amp; NBA Mastery</Button>
      <Button primary onPress={() => go("cardBuilder")}>
        Build a custom card
      </Button>
      <Section>Body &amp; position</Section>
      <Card>
        <Stats
          items={[
            [heightLabel(data.height, data.heightUnit), "HEIGHT"],
            [weightLabel(data.weight, data.weightUnit), "WEIGHT"],
            [data.position || "—", "POSITION"],
          ]}
        />
        <Row style={{ marginTop: 12, justifyContent: "space-between" }}>
          <T kind="mono" style={{ flex: 1 }}>
            EXPERIENCE · {(data.experience || "—").toUpperCase()}
          </T>
          <Chip
            onPress={() => {
              setEditing(true);
              go("height");
            }}
          >
            Edit
          </Chip>
        </Row>
        <Chip
          style={{ marginTop: 8, alignSelf: "flex-start" }}
          onPress={() => {
            setEditing(true);
            go("athlete");
          }}
        >
          Edit athlete
        </Chip>
      </Card>
      <Section>Titles</Section>
      <Card>
        <Row style={{ gap: 4, justifyContent: "space-between" }}>
          {NR_TRACKS.map((t) => (
            <View key={t.k} style={{ alignItems: "center", flex: 1, gap: 3 }}>
              <TitleBadge
                name={t.k}
                size={44}
                rank={ev.ranks[t.k]}
                locked={!ev.ranks[t.k]}
              />
              <T kind="mono" style={{ fontSize: 8.5, textAlign: "center" }}>
                {t.name}
              </T>
            </View>
          ))}
        </Row>
        <Row style={{ marginTop: 12, justifyContent: "space-between" }}>
          <T kind="mono" style={{ flex: 1 }}>
            {Object.keys(ev.spec).length} / 19 SPECIAL · {title.toUpperCase()}
          </T>
          <Chip
            onPress={() => {
              setHistoryTab("Titles");
              go("history");
            }}
          >
            Open
          </Chip>
        </Row>
      </Card>
      <Section>Equipped title</Section>
      <Card>
        <Row style={{ justifyContent: "space-between" }}>
          <T kind="strong" style={{ flex: 1 }}>
            {title}
          </T>
          <Chip
            onPress={() => {
              setHistoryTab("Titles");
              go("history");
            }}
          >
            Change
          </Chip>
        </Row>
      </Card>
      {!!data.games.length && (
        <>
          <Section>Recent activity</Section>
          {data.games
            .slice(-4)
            .reverse()
            .map((g) => (
              <Card key={g.id} style={{ paddingVertical: 12, marginBottom: 8 }}>
                <Row style={{ justifyContent: "space-between" }}>
                  <T style={{ fontSize: 13 }}>{g.date} · Logged game</T>
                  <T kind="mono">
                    {g.pts} pts · {g.ast} ast · {g.reb} reb
                  </T>
                </Row>
              </Card>
            ))}
        </>
      )}
    </>
  );
}
export function CardBuilder() {
  const { data, setData, go, colors } = useApp(),
    [error, setError] = useState("");
  const c = data.card,
    patch = (p: Partial<CardOptions>) =>
      setData((d) => ({ ...d, card: { ...d.card, ...p } }));
  async function photo() {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        quality: 1,
      });
      if (!result.canceled)
        patch({ image: await keepImage(result.assets[0].uri) });
    } catch {
      setError("Could not open your photos. Try again.");
    }
  }
  const options = (title: string, arr: string[], key: keyof CardOptions) => (
    <Card>
      <T kind="h3" style={{ marginBottom: 10 }}>
        {title}
      </T>
      <Chips
        options={arr}
        value={String(c[key])}
        onChange={(v) => patch({ [key]: v })}
      />
    </Card>
  );
  return (
    <>
      <Row style={{ marginBottom: 10 }}>
        <Button
          style={{ width: 40, padding: 8, margin: 0 }}
          onPress={() => go("profile")}
        >
          ‹
        </Button>
        <T kind="h2">Custom card</T>
      </Row>
      <PlayerCard options={c} />
      <T kind="mono" style={{ textAlign: "center", marginBottom: 12 }}>
        Tap the card to flip
      </T>
      <Button primary onPress={photo}>
        {c.image ? "Change selfie" : "Upload selfie"}
      </Button>
      {error && <T style={{ color: "#ef4444" }}>{error}</T>}
      <Card>
        <T kind="h3">Identity</T>
        <Input
          placeholder="Player name"
          value={c.name}
          maxLength={18}
          onChangeText={(v) => patch({ name: v })}
          style={{ marginTop: 10 }}
        />
        <Row>
          <View style={{ flex: 1 }}>
            <Input
              placeholder="#"
              value={c.num}
              maxLength={2}
              keyboardType="number-pad"
              onChangeText={(v) => patch({ num: v.replace(/\D/g, "") })}
            />
          </View>
          <Chips
            options={["PG", "SG", "SF", "PF", "C"]}
            value={c.pos}
            onChange={(v) => patch({ pos: v })}
          />
        </Row>
      </Card>
      <Card>
        <T kind="h3" style={{ marginBottom: 10 }}>
          Series
        </T>
        <Chips
          options={design.styles.map((s) => String(s[0]))}
          value={c.style}
          onChange={(v) => {
            const s = design.styles.find((s) => s[0] === v)!;
            patch({ style: v, c1: String(s[1]), c2: String(s[2]) });
          }}
        />
      </Card>
      {options("Pattern", design.patterns, "pat")}
      {options("Shape", Object.keys(design.shapes), "shape")}
      {options("Frame", ["Neon", "Double", "Chrome", "None"], "frame")}
      {options("Typeface", design.fonts, "font")}
      <Card>
        <T kind="h3">Colors</T>
        <Row style={{ marginTop: 10 }}>
          <View style={{ flex: 1 }}>
            <Input
              label="Primary color"
              value={c.c1}
              onChangeText={(v) => patch({ c1: v })}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Input
              label="Secondary color"
              value={c.c2}
              onChangeText={(v) => patch({ c2: v })}
            />
          </View>
        </Row>
        <Row style={{ justifyContent: "space-between" }}>
          <T kind="muted">Holo shine</T>
          <Toggle
            label="Holo shine"
            value={c.shine}
            onChange={() => patch({ shine: !c.shine })}
          />
        </Row>
      </Card>
      <Button
        primary
        onPress={() => {
          patch({ useCustom: true });
          go("profile");
        }}
      >
        {c.useCustom ? "✓ Using as my player card" : "Use as my player card"}
      </Button>
      {c.useCustom && (
        <Button
          onPress={() => {
            patch({ useCustom: false });
            go("profile");
          }}
        >
          Back to default card
        </Button>
      )}
    </>
  );
}
