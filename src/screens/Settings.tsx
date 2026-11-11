import React, { useState } from "react";
import { View, Modal, Pressable, Share, Platform } from "react-native";
import * as Sharing from "expo-sharing";
import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system/legacy";
import { useApp } from "../state/AppContext";
import {
  Art,
  Button,
  Card,
  Chip,
  Input,
  Row,
  Section,
  Segments,
  Slider,
  T,
  Toggle,
} from "../components/ui";
export function Settings() {
  const { data, setData, go, colors, reset } = useApp(),
    [deleting, setDeleting] = useState(false),
    [resetting, setResetting] = useState(false),
    [queue, setQueue] = useState(false),
    [note, setNote] = useState(""),
    [soundTab, setSoundTab] = useState(false),
    [legal, setLegal] = useState("");
  const patch = (p: Partial<typeof data>) => setData((d) => ({ ...d, ...p }));
  async function exportSave() {
    try {
      const text = JSON.stringify(
        {
          type: "nextrun-native-save",
          version: 1,
          data: { ...data, account: null },
        },
        null,
        2,
      );
      if (Platform.OS === "web") {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(
          new Blob([text], { type: "application/json" }),
        );
        a.download = "NextRun-save.json";
        a.click();
        URL.revokeObjectURL(a.href);
      } else {
        const path = FileSystem.cacheDirectory + "NextRun-save.json";
        await FileSystem.writeAsStringAsync(path, text);
        await Sharing.shareAsync(path, {
          mimeType: "application/json",
          dialogTitle: "NextRun save",
        });
      }
      setNote("Save exported.");
    } catch {
      setNote("Could not export your save.");
    }
  }
  async function importSave() {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ["application/json", "text/plain"],
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;
      const f = result.assets[0];
      const text =
        Platform.OS === "web"
          ? await (await fetch(f.uri)).text()
          : await FileSystem.readAsStringAsync(f.uri);
      const j = JSON.parse(text);
      if (
        j.type !== "nextrun-native-save" ||
        j.version !== 1 ||
        !j.data ||
        !Array.isArray(j.data.games) ||
        !Array.isArray(j.data.friends) ||
        !j.data.card ||
        !["light", "dark"].includes(j.data.theme)
      )
        throw Error();
      setData((d) => ({ ...d, ...j.data, account: d.account }));
      setNote("Save imported.");
    } catch {
      setNote("That is not a valid NextRun save file.");
    }
  }
  return (
    <>
      <Row style={{ marginBottom: 14 }}>
        <Button
          style={{ width: 42, height: 44, padding: 0, margin: 0 }}
          onPress={() => go("profile")}
        >
          ‹
        </Button>
        <T kind="h2">Settings</T>
      </Row>
      <View
        style={{
          height: 152,
          borderRadius: 24,
          overflow: "hidden",
          padding: 18,
          justifyContent: "flex-end",
          marginBottom: 12,
          borderWidth: 1,
          borderColor: colors.edge,
          backgroundColor: data.theme === "light" ? "#fff3e8" : "#15100b",
        }}
      >
        <Art
          name="ball"
          style={{
            position: "absolute",
            right: -26,
            top: -24,
            width: 190,
            height: 190,
          }}
        />
        <T kind="hud">NextRun</T>
        <T kind="h2" style={{ marginTop: 2 }}>
          NextRun Lab
        </T>
        <T kind="muted">Turn on your potential.</T>
      </View>
      <Card>
        <Row style={{ justifyContent: "space-between" }}>
          <View>
            <T kind="strong">Light mode</T>
            <T kind="mono">
              {data.theme === "dark"
                ? "Bulb is on (dark mode)"
                : "Bulb is off (light mode)"}
            </T>
          </View>
          <Toggle
            label="Light mode"
            value={data.theme === "light"}
            onChange={() =>
              patch({ theme: data.theme === "light" ? "dark" : "light" })
            }
          />
        </Row>
      </Card>
      <Card>
        <Row style={{ justifyContent: "space-between" }}>
          <View>
            <T kind="h3">Sound</T>
            <T kind="muted" style={{ marginTop: 4 }}>
              UI, game and reward sounds.
            </T>
          </View>
          <Toggle
            value={data.sound}
            label="Sound effects"
            onChange={() => patch({ sound: !data.sound })}
          />
        </Row>
        <Slider
          min={0}
          max={1}
          value={data.volume}
          onChange={(v) => patch({ volume: v })}
          label="Sound volume"
        />
        <T kind="mono">VOLUME · {Math.round(data.volume * 100)}%</T>
      </Card>
      <Card>
        <T kind="h3">Save &amp; restore</T>
        <T kind="muted" style={{ marginTop: 4, marginBottom: 10 }}>
          Your player, stats and card stay on this device. Export a save to keep
          a copy.
        </T>
        <Button primary onPress={exportSave}>
          Export save
        </Button>
        <Button onPress={importSave}>Import save</Button>
        {!!note && <T kind="mono">{note}</T>}
      </Card>
      <Card>
        <T kind="h3">Location</T>
        <T kind="muted" style={{ marginTop: 4, marginBottom: 10 }}>
          Type your city or campus to find clubs and runs near you. It stays on
          this device.
        </T>
        <Input
          placeholder="City, State (e.g. Dallas, TX)"
          value={data.location}
          maxLength={60}
          onChangeText={(v) => patch({ location: v })}
          style={{ margin: 0 }}
        />
      </Card>
      <Card>
        <T kind="h3">Account</T>
        <T kind="muted" style={{ marginTop: 4 }}>
          {data.email || "Not signed in"}
        </T>
      </Card>
      <Card>
        <T kind="h3">Privacy</T>
        <T kind="muted" style={{ marginTop: 4, marginBottom: 10 }}>
          Who can see your profile and stats.
        </T>
        <Segments
          options={["Public", "Club", "Private"]}
          value={data.privacy}
          onChange={(v) => patch({ privacy: v })}
        />
      </Card>
      <Card>
        <Pressable onPress={() => setQueue(!queue)}>
          <Row style={{ justifyContent: "space-between" }}>
            <T kind="h3">Processing queue</T>
            <T kind="mono">{queue ? "HIDE" : "0 UPLOADING"}</T>
          </Row>
        </Pressable>
        {queue && (
          <T kind="muted" style={{ marginTop: 10 }}>
            No uploads in the queue.
          </T>
        )}
      </Card>
      <Card>
        <T kind="h3">Legal</T>
        <Pressable
          onPress={() => setLegal("Terms of Service")}
          style={{ paddingTop: 8, minHeight: 44 }}
        >
          <T style={{ color: "#FF6A00" }}>Terms of Service</T>
        </Pressable>
        <Pressable
          onPress={() => setLegal("Privacy Policy")}
          style={{ minHeight: 44 }}
        >
          <T style={{ color: "#FF6A00" }}>Privacy Policy</T>
        </Pressable>
      </Card>
      <Button
        style={resetting ? { borderColor: "#ef4444" } : undefined}
        onPress={() => {
          if (resetting) reset();
          else setResetting(true);
        }}
      >
        {resetting
          ? "Tap again to erase and start over"
          : "Reset to a new player"}
      </Button>
      <Button
        style={{ borderColor: "#ef4444" }}
        onPress={() => setDeleting(true)}
      >
        <T style={{ color: "#ef4444", fontFamily: "Inter-600", fontSize: 15 }}>
          Delete account
        </T>
      </Button>
      <T kind="mono" style={{ textAlign: "center", marginTop: 6 }}>
        NextRun · Version 1.0.0
      </T>
      <Modal
        transparent
        visible={deleting || !!legal}
        animationType="fade"
        onRequestClose={() => {
          setDeleting(false);
          setLegal("");
        }}
      >
        <View
          style={{
            flex: 1,
            backgroundColor: "rgba(0,0,0,.7)",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
          }}
        >
          <Card
            style={{
              width: "100%",
              maxWidth: 360,
              padding: 20,
              borderColor: "#ef4444",
            }}
          >
            <T kind="h2">{legal || "Delete account?"}</T>
            <T kind="muted" style={{ marginTop: 8, marginBottom: 16 }}>
              {legal
                ? "The supplied HTML includes this label, but no policy document or link."
                : "This permanently removes your card, stats, and uploaded footage. This can’t be undone."}
            </T>
            {!legal && (
              <Button
                style={{ backgroundColor: "#ef4444", borderWidth: 0 }}
                onPress={() => {
                  setDeleting(false);
                  reset();
                }}
              >
                <T style={{ color: "#fff" }}>Delete permanently</T>
              </Button>
            )}
            <Button
              onPress={() => {
                setDeleting(false);
                setLegal("");
              }}
            >
              {legal ? "Close" : "Keep account"}
            </Button>
          </Card>
        </View>
      </Modal>
    </>
  );
}
