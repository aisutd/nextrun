import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { Badge, Button, Card, Label, Row } from "./ui";
import { useTheme } from "../theme/theme";
import {
  BenchmarkState,
  getBenchmark,
  getMetrics,
  Improvement,
  MetricsReport,
  ModelReport,
  startBenchmark,
} from "../lib/api";

// Camera → Models: accuracy of every model from the recorded test-set runs (GET /metrics), and inference speed
// measured on the computer running the API (POST /metrics/benchmark).
const GOOD = "#16a34a",
  BAD = "#dc2626";
const pct = (x: number | null | undefined, d = 1) => (x == null ? "—" : `${(x * 100).toFixed(d)}%`);
const num = (x: number | null | undefined, d = 3) => (x == null ? "—" : x.toFixed(d));
const ms = (x: number) => (x >= 100 ? `${Math.round(x)} ms` : `${x.toFixed(1)} ms`);
const count = (x: number, ratio?: boolean) => (ratio ? pct(x) : x.toLocaleString());

export function ModelMetrics() {
  const [report, setReport] = useState<MetricsReport | null>(null),
    [bench, setBench] = useState<BenchmarkState | null>(null),
    [err, setErr] = useState("");

  useEffect(() => {
    getMetrics().then(setReport).catch((e) => setErr(`${(e as Error).message}. Is the NextRun API running?`));
    getBenchmark().then(setBench).catch(() => {});
  }, []);
  useEffect(() => {
    if (!bench?.running) return;
    const id = setInterval(() => getBenchmark().then(setBench).catch(() => {}), 1500);
    return () => clearInterval(id);
  }, [bench?.running]);

  async function runSpeedTest() {
    try {
      setBench(await startBenchmark());
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (err) return <Card style={{ marginTop: 12 }}><Label kind="muted">{err}</Label></Card>;
  if (!report) return <Card style={{ marginTop: 12 }}><Label kind="muted">Loading model metrics…</Label></Card>;
  return (
    <View style={{ marginTop: 12, gap: 12 }}>
      <Card>
        <Label kind="h3">Model metrics</Label>
        <Label kind="muted" style={{ marginTop: 4 }}>
          Precision, recall, F1, mAP@0.5 and mAP@0.5:0.95 on held-out test sets, how much each model cut errors and
          lost data versus the version it replaced, and how fast each one runs.
        </Label>
      </Card>
      <SpeedCard bench={bench} onRun={runSpeedTest} />
      {report.models.map((m) => (
        <ModelCard key={m.key} m={m} />
      ))}
      <Label kind="mono" style={{ textAlign: "center" }}>Source: {report.source}</Label>
    </View>
  );
}

function SpeedCard({ bench, onRun }: { bench: BenchmarkState | null; onRun: () => void }) {
  const t = useTheme();
  const b = bench?.result;
  return (
    <Card>
      <Row between>
        <Label kind="h3">Inference speed & latency</Label>
        {b && <Badge>{b.device.toUpperCase()}</Badge>}
      </Row>
      {b ? (
        <>
          <Label kind="muted" style={{ marginTop: 4 }}>
            Measured on this computer {b.measured_at}: {b.runs} timed runs per model on {b.frame} ({b.frame_size[0]}×{b.frame_size[1]}).
          </Label>
          <TableHead cols={["MODEL", "INPUT", "P50", "P95", "FPS"]} />
          {b.models.map((r) => (
            <TableRow
              key={`${r.key}-${r.imgsz}`}
              cells={[`${r.name}${r.use === "live" ? " (live)" : ""}`, `${r.imgsz}px`, ms(r.p50_ms), ms(r.p95_ms), r.fps.toFixed(1)]}
            />
          ))}
          <Text style={{ color: t.text, marginTop: 8, fontSize: 12 }}>
            Live detection model time per frame (players + ball): <Text style={{ fontWeight: "800", color: t.accent }}>{ms(b.live_frame_ms)}</Text>
            {` ≈ ${(1000 / b.live_frame_ms).toFixed(1)} frames/s before network time.`}
          </Text>
        </>
      ) : (
        <Label kind="muted" style={{ marginTop: 4 }}>
          {bench?.error ? `Speed test failed: ${bench.error}` : "Time every model on a real game frame on the computer running NextRun."}
        </Label>
      )}
      <Button onPress={onRun} disabled={!!bench?.running} style={{ borderRadius: 999, paddingVertical: 9, marginTop: 10, marginBottom: 0 }} textStyle={{ fontSize: 12 }}>
        {bench?.running ? "Measuring… (about 20 s)" : b ? "Run speed test again" : "Run speed test"}
      </Button>
    </Card>
  );
}

function ModelCard({ m }: { m: ModelReport }) {
  const h = m.headline;
  return (
    <Card>
      <Label kind="h3">{m.name}</Label>
      <Label kind="mono" style={{ marginTop: 2 }}>{m.weights}</Label>
      <Label kind="muted" style={{ marginTop: 4 }}>Test data: {m.dataset}</Label>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
        <Tile label="Precision" value={pct(h.precision)} />
        <Tile label="Recall" value={pct(h.recall)} />
        <Tile label="F1" value={num(h.f1)} />
        <Tile label="mAP@0.5" value={num(h.map50)} />
        <Tile label="mAP@0.5:0.95" value={num(h.map50_95)} />
      </View>
      {m.headline_note && <Label kind="muted" style={{ marginTop: 6, fontSize: 11 }}>{m.headline_note}</Label>}
      <Label kind="muted" style={{ marginTop: 6, fontSize: 11 }}>IoU: {m.iou_rule}</Label>
      <Details m={m} />
      <Label kind="hud" style={{ marginTop: 14 }}>vs {m.baseline}</Label>
      {m.improvements.map((i) => (
        <ImprovementRow key={i.label} i={i} />
      ))}
    </Card>
  );
}

function Details({ m }: { m: ModelReport }) {
  if (m.classes)
    return (
      <>
        <TableHead cols={["CLASS", "PREC", "RECALL", "F1", "mAP@.5"]} />
        {m.classes.map((c) => (
          <TableRow key={c.name} cells={[c.name, pct(c.precision), pct(c.recall), num(c.f1), num(c.map50)]} />
        ))}
        <Label kind="muted" style={{ marginTop: 6, fontSize: 11 }}>
          Averaged over the test sets, weighted by images.
          {m.validation ? ` Validation split (best epoch ${m.validation.epoch}): mAP@0.5 ${num(m.validation.map50)}, mAP@0.5:0.95 ${num(m.validation.map50_95)}, F1 ${num(m.validation.f1)}.` : ""}
          {m.gpu_speed ? ` Test-run speed on ${m.gpu_speed.device}: ${ms(m.gpu_speed.inference_ms)} inference, ${ms(m.gpu_speed.total_ms)} total per image.` : ""}
        </Label>
      </>
    );
  if (m.court)
    return (
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
        <Tile label="Court found" value={pct(m.court.found_rate)} small />
        <Tile label="Usable (≤3 ft)" value={pct(m.court.usable_rate)} small />
        <Tile label="Median error" value={`${m.court.median_error_ft.toFixed(2)} ft`} small />
        <Tile label="Synthetic views" value={pct(m.court.synthetic_usable_rate)} small />
        <Tile label="Handheld phones" value={pct(m.court.handheld_usable_rate)} small />
      </View>
    );
  if (m.tracking)
    return (
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
        <Tile label="MOTA" value={num(m.tracking.mota)} small />
        <Tile label="IDF1" value={num(m.tracking.idf1)} small />
        <Tile label="ID switches" value={m.tracking.id_switches.toLocaleString()} small />
        <Tile label="True positives" value={m.tracking.tp.toLocaleString()} small />
        <Tile label="False positives" value={m.tracking.fp.toLocaleString()} small />
        <Tile label="False negatives" value={m.tracking.fn.toLocaleString()} small />
      </View>
    );
  if (m.events)
    return (
      <>
        <TableHead cols={["EVENT", "PREC", "RECALL", "F1", "FP / FN"]} />
        {m.events.map((e) => (
          <TableRow key={e.name} cells={[e.name, pct(e.precision, 0), pct(e.recall, 0), num(e.f1, 2), `${e.fp} / ${e.fn}`]} />
        ))}
      </>
    );
  return null;
}

function ImprovementRow({ i }: { i: Improvement }) {
  const t = useTheme();
  const better = i.change != null && i.change < 0,
    worse = i.change != null && i.change > 0;
  return (
    <Row between style={{ paddingVertical: 6, borderTopWidth: 1, borderColor: t.border }}>
      <View style={{ flex: 1, paddingRight: 8 }}>
        <Text style={{ color: t.text, fontSize: 12 }}>{i.label}</Text>
        <Text style={{ color: t.muted, fontSize: 11 }}>
          {count(i.before, i.ratio)} → {count(i.after, i.ratio)}
          {i.of ? ` of ${i.of}` : ""} · {i.kind}
        </Text>
      </View>
      <Text style={{ fontSize: 14, fontWeight: "800", color: better ? GOOD : worse ? BAD : t.muted }}>
        {i.change == null ? "—" : `${better ? "▼" : worse ? "▲" : ""} ${Math.abs(i.change * 100).toFixed(0)}%`}
      </Text>
    </Row>
  );
}

function Tile({ label, value, small }: { label: string; value: string; small?: boolean }) {
  const t = useTheme();
  return (
    <View style={{ minWidth: small ? 92 : 100, flexGrow: 1, borderWidth: 1, borderColor: t.border, borderRadius: 14, padding: 10, backgroundColor: t.surface2 }}>
      <Text style={{ color: t.accent, fontSize: small ? 16 : 20, fontWeight: "800", fontVariant: ["tabular-nums"] }}>{value}</Text>
      <Text style={{ color: t.muted, fontSize: 10, letterSpacing: 0.5, marginTop: 2 }}>{label}</Text>
    </View>
  );
}

function TableHead({ cols }: { cols: string[] }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: "row", marginTop: 12, paddingBottom: 4, borderBottomWidth: 1, borderColor: t.border }}>
      {cols.map((c, i) => (
        <Text key={c} style={{ flex: i ? 1 : 2, color: t.muted, fontSize: 10, letterSpacing: 0.5, textAlign: i ? "right" : "left" }}>{c}</Text>
      ))}
    </View>
  );
}

function TableRow({ cells }: { cells: string[] }) {
  const t = useTheme();
  return (
    <View style={{ flexDirection: "row", paddingVertical: 5 }}>
      {cells.map((c, i) => (
        <Text key={i} style={{ flex: i ? 1 : 2, color: t.text, fontSize: 12, textAlign: i ? "right" : "left", fontVariant: ["tabular-nums"] }}>{c}</Text>
      ))}
    </View>
  );
}
