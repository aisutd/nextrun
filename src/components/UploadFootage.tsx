import React from "react";
import { Image, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { useApp } from "../state/AppState";
import { Button, Card, Label, Scene, Progress, Row, Badge } from "./ui";
import { artwork } from "../theme/artwork";
export function UploadFootage() {
  const { s, upload } = useApp();
  async function choose() {
    const r = await DocumentPicker.getDocumentAsync({
      type: "video/*",
      copyToCacheDirectory: false,
    });
    if (!r.canceled) upload(r.assets[0].name);
  }
  return (
    <Card>
      <Label kind="h3" style={{ textAlign: "center" }}>
        Upload game footage
      </Label>
      <Scene
        name="gate"
        style={{ height: 190, marginTop: 8, borderRadius: 14 }}
      >
        <Image
          source={artwork["upload-hoop"]}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
          }}
          resizeMode="contain"
        />
        {s.uploading && (
          <Label
            style={{
              position: "absolute",
              top: "55%",
              left: "45%",
              fontSize: 26,
            }}
          >
            ▶
          </Label>
        )}
      </Scene>
      <Label
        kind="muted"
        style={{ textAlign: "center", marginTop: 6, marginBottom: 10 }}
      >
        {s.uploading
          ? "Sinking it…"
          : s.uploadName
            ? `✓ ${s.uploadName} queued for processing`
            : "Drag a game video here or choose a file."}
      </Label>
      <Button
        onPress={choose}
        style={{ borderRadius: 999, paddingVertical: 10, marginBottom: 0 }}
        textStyle={{ fontSize: 12 }}
      >
        Choose video
      </Button>
    </Card>
  );
}
export function Queue() {
  const { s } = useApp();
  return (
    <Card>
      <Row between>
        <Label kind="h3">Processing queue</Label>
        <Badge>{2 + (s.uploadName && !s.uploading ? 1 : 0)} IN QUEUE</Badge>
      </Row>
      {[
        ["Sat_run_full.mp4", 64],
        ["Drills_Tue.mp4", 18],
        ...(s.uploadName && !s.uploading ? [[s.uploadName, 3]] : []),
      ].map(([n, p]) => (
        <View key={n}>
          <Label kind="mono" style={{ marginTop: 12 }}>
            {n} — {p === 3 ? "queued" : `${p}%`}
          </Label>
          <Progress value={Number(p)} />
        </View>
      ))}
    </Card>
  );
}
