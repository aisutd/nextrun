import React, { useEffect, useState } from "react";
import { View, Pressable, useWindowDimensions, Image } from "react-native";
import * as Crypto from "expo-crypto";
import { useApp, heightLabel, weightLabel } from "../state/AppContext";
import {
  Art,
  Button,
  Card,
  Chips,
  Dots,
  Icon,
  Input,
  Logo,
  Row,
  Segments,
  Slider,
  T,
} from "../components/ui";
import { accent } from "../theme/tokens";
import design from "../data/design.json";
import { assets } from "../theme/assets";
export function Intro() {
  const { go, setAccountMode } = useApp(),
    { height } = useWindowDimensions(),
    [slide, setSlide] = useState(0);
  useEffect(() => {
    const t = setInterval(
      () => setSlide((s) => (s + 1) % design.onboarding.length),
      6200,
    );
    return () => clearInterval(t);
  }, []);
  const o = design.onboarding[slide];
  const h = o.h.split(/(<span class="or">|<\/span>)/);
  let orange = false;
  return (
    <View style={{ minHeight: height - 42, paddingTop: 6 }}>
      <Art
        name={`intro-${slide}`}
        style={{
          position: "absolute",
          top: -18,
          left: -16,
          right: -16,
          width: undefined,
          height: height * 0.92,
        }}
        resizeMode="stretch"
      />
      <Row
        style={{ justifyContent: "space-between", alignItems: "flex-start" }}
      >
        <Logo />
        <T
          kind="mono"
          style={{
            fontSize: 10,
            lineHeight: 14.5,
            letterSpacing: 2,
            textAlign: "right",
          }}
        >
          {o.t.replace(/<br>/g, "\n")}
        </T>
      </Row>
      <View style={{ marginTop: "auto", paddingTop: height * 0.46 }}>
        <T
          kind="h1"
          style={{
            fontSize: 34,
            lineHeight: 35.36,
            marginBottom: 10,
            textTransform: "uppercase",
          }}
        >
          {h.map((s, i) => {
            if (s.includes("<span")) {
              orange = true;
              return null;
            }
            if (s === "</span>") {
              orange = false;
              return null;
            }
            return (
              <T
                key={i}
                kind="h1"
                style={{
                  fontSize: 34,
                  lineHeight: 35.36,
                  color: orange ? accent : undefined,
                }}
              >
                {s}
              </T>
            );
          })}
        </T>
        <T kind="muted" style={{ marginBottom: 18, maxWidth: 290 }}>
          {o.p}
        </T>
        <Button
          primary
          onPress={() => {
            setAccountMode("create");
            go("account");
          }}
        >
          <Icon name="mail" size={20} color="#fff" />
          <T style={{ color: "#fff", fontSize: 15, fontFamily: "Inter-600" }}>
            Continue with email
          </T>
        </Button>
        <Button
          onPress={() => {
            setAccountMode("create");
            go("account");
          }}
        >
          <T
            style={{ fontSize: 18, color: "#4285f4", fontFamily: "Inter-600" }}
          >
            G
          </T>
          <T style={{ fontFamily: "Inter-600", fontSize: 15 }}>
            Continue with Google
          </T>
        </Button>
        <Button
          onPress={() => {
            setAccountMode("create");
            go("account");
          }}
        >
          <Image source={assets.apple} style={{ width: 20, height: 20 }} />
          <T style={{ fontFamily: "Inter-600", fontSize: 15 }}>
            Continue with Apple
          </T>
        </Button>
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            setAccountMode("login");
            go("account");
          }}
          style={{ padding: 10, minHeight: 44, alignItems: "center" }}
        >
          <T style={{ fontSize: 13, color: accent, fontFamily: "Inter-600" }}>
            I already have an account · Log in
          </T>
        </Pressable>
        <T kind="mono" style={{ textAlign: "center", marginTop: 2 }}>
          Track. Improve. Compete. Together.
        </T>
        <Row style={{ justifyContent: "center", gap: 6, marginTop: 12 }}>
          {design.onboarding.map((_, i) => (
            <Pressable
              key={i}
              accessibilityRole="button"
              accessibilityLabel={`Slide ${i + 1}`}
              onPress={() => setSlide(i)}
              style={{
                width: i === slide ? 42 : 24,
                height: 16,
                justifyContent: "center",
              }}
            >
              <View
                style={{
                  height: 4,
                  borderRadius: 6,
                  backgroundColor: i === slide ? accent : "#E7E8EC",
                }}
              />
            </Pressable>
          ))}
        </Row>
      </View>
    </View>
  );
}
export function Account() {
  const { data, setData, go, accountMode } = useApp(),
    [create, setCreate] = useState(accountMode === "create"),
    [email, setEmail] = useState(""),
    [handle, setHandle] = useState(""),
    [pw, setPw] = useState(""),
    [confirm, setConfirm] = useState(""),
    [show, setShow] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email),
    validHandle = /^[a-z0-9_]{3,16}$/i.test(handle.replace(/^@/, "")),
    ok =
      validEmail &&
      (create
        ? validHandle && pw.length >= 8 && pw === confirm
        : pw.length > 0);
  async function submit() {
    if (!ok || busy) return;
    setBusy(true);
    try {
      if (create) {
        const salt = Crypto.randomUUID(),
          hash = await Crypto.digestStringAsync(
            Crypto.CryptoDigestAlgorithm.SHA256,
            salt + "|" + pw,
          );
        setData((d) => ({
          ...d,
          email: email.trim().toLowerCase(),
          handle: "@" + handle.replace(/^@/, ""),
          account: { salt, hash },
        }));
        go("athlete");
      } else {
        if (data.email !== email.trim().toLowerCase() || !data.account) {
          setError(
            "No account with that email on this device. Create one instead.",
          );
          return;
        }
        const hash = await Crypto.digestStringAsync(
          Crypto.CryptoDigestAlgorithm.SHA256,
          data.account.salt + "|" + pw,
        );
        if (hash !== data.account.hash) {
          setError("That password is not right.");
          return;
        }
        go(data.done ? "home" : "athlete");
      }
    } finally {
      setBusy(false);
      setPw("");
      setConfirm("");
    }
  }
  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    placeholder: string,
    secure = false,
    hint = "",
  ) => (
    <View style={{ marginBottom: 12 }}>
      <T
        kind="mono"
        style={{
          fontSize: 10,
          letterSpacing: 1.6,
          marginHorizontal: 2,
          marginBottom: 6,
          textTransform: "uppercase",
        }}
      >
        {label}
      </T>
      <Input
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        secureTextEntry={secure && !show}
        keyboardType={label === "Email" ? "email-address" : "default"}
        style={{ marginBottom: 0, paddingRight: secure ? 48 : 13 }}
      />
      {secure && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={show ? "Hide password" : "Show password"}
          onPress={() => setShow(!show)}
          style={{
            position: "absolute",
            right: 2,
            top: 20,
            width: 48,
            height: 48,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <T style={{ fontSize: 20 }}>◉</T>
        </Pressable>
      )}
      <T
        kind="muted"
        style={{
          fontSize: 11.5,
          marginTop: 6,
          minHeight: 16,
          color:
            label === "Player handle" && validHandle ? "#22c55e" : undefined,
        }}
      >
        {hint}
      </T>
    </View>
  );
  return (
    <View style={{ paddingTop: 8 }}>
      <Row style={{ justifyContent: "space-between" }}>
        <T kind="hud">{create ? "Create account" : "Welcome back"}</T>
        <T kind="mono">{create ? "STEP 1" : "LOG IN"}</T>
      </Row>
      <T kind="h1" style={{ marginTop: 8 }}>
        {create ? "Create your account" : "Log in"}
      </T>
      <T kind="muted" style={{ marginTop: 8, marginBottom: 18 }}>
        {create
          ? "Your account keeps your card, stats and titles safe on this device."
          : "Use the email and password you signed up with on this device."}
      </T>
      {field(
        "Email",
        email,
        setEmail,
        "you@email.com",
        false,
        email && !validEmail ? "Enter a valid email address." : "",
      )}
      {create &&
        field(
          "Player handle",
          handle,
          setHandle,
          "@playername",
          false,
          validHandle
            ? "Looks good. This handle is yours for good."
            : "3–16 characters: letters, numbers, underscore. It is permanent.",
        )}
      {field(
        "Password",
        pw,
        setPw,
        create ? "At least 8 characters" : "Your password",
        true,
        create
          ? "Mix upper and lower case, a number and a symbol for a stronger password."
          : "",
      )}
      {create &&
        field(
          "Retype password",
          confirm,
          setConfirm,
          "Type it again",
          true,
          confirm
            ? pw === confirm
              ? "Passwords match."
              : "Passwords do not match."
            : "",
        )}
      {!!error && <T style={{ color: "#ef4444", marginBottom: 10 }}>{error}</T>}
      <Button primary disabled={!ok || busy} onPress={submit}>
        {busy ? "Please wait…" : create ? "Create account" : "Log in"}
      </Button>
      <Pressable
        onPress={() => {
          setCreate(!create);
          setError("");
          setPw("");
          setConfirm("");
        }}
        style={{ padding: 12, alignItems: "center" }}
      >
        <T style={{ fontSize: 13, color: accent, fontFamily: "Inter-600" }}>
          {create
            ? "I already have an account · Log in"
            : "New here? Create an account"}
        </T>
      </Pressable>
      {create && <Dots step={1} />}
    </View>
  );
}
export function AthleteSetup() {
  const { route, go, data, setData, editing, setEditing, colors } = useApp(),
    { height } = useWindowDimensions();
  const patch = (p: Partial<typeof data>) => setData((d) => ({ ...d, ...p }));
  const step =
    route === "athlete"
      ? 1
      : route === "height"
        ? 2
        : route === "weight"
          ? 3
          : 4;
  const h = heightLabel(data.height, data.heightUnit),
    w = weightLabel(data.weight, data.weightUnit);
  return (
    <View style={{ paddingTop: 10 }}>
      <Row
        style={{
          justifyContent: "space-between",
          paddingBottom: 8,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
        }}
      >
        <T kind="hud">
          {route === "athlete" ? "Athlete select" : "Subject calibration"}
        </T>
        <T kind="mono">{editing ? "EDIT" : `0${step - 1} / 03`}</T>
      </Row>
      <T kind="h1" style={{ marginTop: 8 }}>
        {route === "athlete"
          ? "Choose your athlete"
          : route === "height"
            ? "How tall are you?"
            : route === "weight"
              ? "Your weight"
              : "Your game"}
      </T>
      {route === "athlete" ? (
        <>
          <T kind="muted" style={{ marginBottom: 12 }}>
            Your NextRun robot-athlete. This is the model you will see across
            the app.
          </T>
          <Row style={{ gap: 10 }}>
            {(["m", "f"] as const).map((s) => (
              <Pressable
                key={s}
                accessibilityRole="button"
                accessibilityState={{ selected: data.sex === s }}
                onPress={() => patch({ sex: s })}
                style={{
                  flex: 1,
                  height: Math.min(height * 0.43, 360),
                  borderWidth: 1,
                  borderColor: data.sex === s ? accent : colors.border,
                  borderRadius: 18,
                  overflow: "hidden",
                  backgroundColor: colors.surface,
                }}
              >
                <Art name={"sex" + s} resizeMode="contain" />
                <T
                  kind="strong"
                  style={{
                    position: "absolute",
                    bottom: 12,
                    alignSelf: "center",
                  }}
                >
                  {s === "m" ? "Male" : "Female"}
                </T>
              </Pressable>
            ))}
          </Row>
          <Button
            primary
            style={{ marginTop: 14 }}
            onPress={() => {
              if (editing) {
                setEditing(false);
                go("profile");
              } else go("height");
            }}
          >
            {editing ? "Save athlete" : "Continue"}
          </Button>
        </>
      ) : route === "height" || route === "weight" ? (
        <>
          <T kind="muted" style={{ marginBottom: 10 }}>
            {route === "height"
              ? "Slide the scale until the model matches your height."
              : "Used for your card and training load. You can change it any time."}
          </T>
          <Segments
            options={route === "height" ? ["ft", "cm"] : ["lbs", "kg"]}
            value={route === "height" ? data.heightUnit : data.weightUnit}
            onChange={(u) =>
              patch(
                route === "height"
                  ? { heightUnit: u as "ft" | "cm" }
                  : { weightUnit: u as "lbs" | "kg" },
              )
            }
          />
          <View
            style={{
              height: Math.max(300, Math.min(height * 0.46, 400)),
              borderWidth: 1,
              borderColor: colors.edge,
              borderRadius: 18,
              backgroundColor: colors.surface,
              overflow: "hidden",
              marginBottom: 14,
            }}
          >
            <Art
              name={route === "height" ? "hgt" : "wgt"}
              resizeMode="contain"
              style={{
                transform:
                  route === "height" ? [{ scale: data.height / 178 }] : [],
              }}
            />
            <View style={{ position: "absolute", left: 14, top: 12 }}>
              <T style={{ fontFamily: "JetBrainsMono-500", fontSize: 34 }}>
                {route === "height" ? h : w}
              </T>
              <T kind="mono" style={{ marginTop: 4 }}>
                {route === "height"
                  ? data.heightUnit === "ft"
                    ? `${data.height} cm`
                    : `${Math.round(data.height / 2.54)} in`
                  : h}
              </T>
            </View>
            {route === "height" && (
              <View
                style={{
                  position: "absolute",
                  right: 0,
                  width: 78,
                  top: 0,
                  bottom: 0,
                  borderLeftWidth: 1,
                  borderLeftColor: colors.edge,
                  padding: 10,
                  justifyContent: "space-around",
                }}
              >
                {[230, 210, 190, 170, 150].map((c) => (
                  <T key={c} kind="mono" style={{ textAlign: "right" }}>
                    {data.heightUnit === "cm" ? c : `${Math.round(c / 30.48)}′`}{" "}
                    ─
                  </T>
                ))}
              </View>
            )}
          </View>
          <Slider
            min={route === "height" ? 140 : 40}
            max={route === "height" ? 230 : 160}
            value={route === "height" ? data.height : data.weight}
            label={route === "height" ? "Height" : "Weight"}
            onChange={(v) =>
              patch(
                route === "height" ? { height: Math.round(v) } : { weight: v },
              )
            }
          />
          {route === "height" ? (
            <Row>
              <Button
                style={{ width: 52, padding: 0 }}
                onPress={() =>
                  patch({ height: Math.max(140, data.height - 1) })
                }
              >
                −
              </Button>
              <Button primary style={{ flex: 1 }} onPress={() => go("weight")}>
                Lock in height
              </Button>
              <Button
                style={{ width: 52, padding: 0 }}
                onPress={() =>
                  patch({ height: Math.min(230, data.height + 1) })
                }
              >
                +
              </Button>
            </Row>
          ) : (
            <Button primary onPress={() => go("gameProfile")}>
              Lock in weight
            </Button>
          )}
        </>
      ) : (
        <>
          <T kind="hud" style={{ marginTop: 12, marginBottom: 8 }}>
            Preferred position
          </T>
          <View className="flex-row flex-wrap gap-2">
            {[
              ["PG", "Point Guard"],
              ["SG", "Shooting Guard"],
              ["SF", "Small Forward"],
              ["PF", "Power Forward"],
              ["C", "Center"],
              ["N/A", "Not sure yet"],
            ].map(([p, l]) => (
              <Pressable
                key={p}
                accessibilityRole="button"
                onPress={() => patch({ position: p })}
                style={{
                  width: "31.5%",
                  flexGrow: 1,
                  minHeight: 76,
                  padding: 12,
                  borderRadius: 14,
                  borderWidth: 1,
                  borderColor: data.position === p ? accent : colors.border,
                  backgroundColor: colors.surface,
                  alignItems: "center",
                }}
              >
                <T
                  kind="h2"
                  style={{
                    fontSize: 22,
                    color: data.position === p ? accent : colors.text,
                  }}
                >
                  {p}
                </T>
                <T kind="muted" style={{ fontSize: 10 }}>
                  {l}
                </T>
              </Pressable>
            ))}
          </View>
          <T kind="hud" style={{ marginTop: 16, marginBottom: 8 }}>
            Experience
          </T>
          {[
            ["Beginner", "New, or just for fun"],
            ["Intermediate", "Regular pickup or rec league"],
            ["Experienced", "Years of competitive play"],
          ].map(([v, l], i) => (
            <Pressable
              key={v}
              onPress={() => patch({ experience: v })}
              style={{
                padding: 12,
                borderRadius: 14,
                borderWidth: 1,
                borderColor: data.experience === v ? accent : colors.border,
                backgroundColor: colors.surface,
                marginBottom: 8,
              }}
            >
              <Row>
                <T style={{ color: accent, letterSpacing: 2 }}>
                  {"▮".repeat(i + 1)}
                  {"▯".repeat(2 - i)}
                </T>
                <View>
                  <T kind="strong">{v}</T>
                  <T kind="muted" style={{ fontSize: 11 }}>
                    {l}
                  </T>
                </View>
              </Row>
            </Pressable>
          ))}
          <Button
            primary
            disabled={!data.position || !data.experience}
            style={{ marginTop: 16 }}
            onPress={() => {
              patch({
                card: {
                  ...data.card,
                  pos: data.position === "N/A" ? "" : data.position,
                },
              });
              if (editing) {
                setEditing(false);
                go("profile");
              } else go("recordTips");
            }}
          >
            {editing ? "Save profile" : "Continue"}
          </Button>
        </>
      )}
      {!editing && <Dots step={step} />}
    </View>
  );
}
export function RecordingTips() {
  const { go } = useApp(),
    [slide, setSlide] = useState(0),
    tips = [
      [
        "Stand back",
        "Keep your phone steady at half-court height so the full court is visible.",
      ],
      [
        "Frame the lines",
        "Line the neon guides up with the baselines and sidelines.",
      ],
      ["Hit record", "Tap the red button. NextRun handles the tracking."],
    ];
  return (
    <View>
      <T kind="h1" style={{ marginTop: 20 }}>
        How to record
      </T>
      <Card
        style={{
          marginTop: 18,
          paddingVertical: 26,
          paddingHorizontal: 16,
          alignItems: "center",
        }}
      >
        <Art
          name="court-guide"
          style={{ height: 117, width: 200 }}
          resizeMode="contain"
        />
        <T kind="h2" style={{ marginTop: 16, marginBottom: 6 }}>
          {tips[slide][0]}
        </T>
        <T kind="muted" style={{ textAlign: "center" }}>
          {tips[slide][1]}
        </T>
        <T kind="mono" style={{ marginTop: 12 }}>
          Swipe or tap to continue
        </T>
      </Card>
      <Dots step={slide} total={3} />
      <Button
        primary
        onPress={() => (slide < 2 ? setSlide(slide + 1) : go("home"))}
      >
        {slide < 2 ? "Next" : "Got it"}
      </Button>
    </View>
  );
}
