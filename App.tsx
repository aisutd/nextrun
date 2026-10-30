import "./global.css";
import React from "react";
import {
  ActivityIndicator,
  BackHandler,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  useWindowDimensions,
  View,
} from "react-native";
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import { useFonts } from "expo-font";
import { fonts } from "./src/theme/fonts";
import { AppState, useApp } from "./src/state/AppState";
import { initialState } from "./src/state/model";
import { gradient, rgba, useTheme } from "./src/theme/theme";
import { Button, Card, Label, Scene } from "./src/components/ui";
import { Navigation } from "./src/components/Navigation";
import { Onboarding, slides } from "./src/screens/Onboarding";
import { Home } from "./src/screens/Home";
import { ClubHub } from "./src/screens/ClubHub";
import { Camera } from "./src/screens/Camera";
import { Friends } from "./src/screens/Friends";
import { Profile } from "./src/screens/Profile";
import { Settings } from "./src/screens/Settings";
import { CardBuilder } from "./src/screens/CardBuilder";
function Application() {
  const { s, patch, go, update } = useApp(),
    t = useTheme(),
    { width, height } = useWindowDimensions(),
    insets = useSafeAreaInsets();
  const wide = width >= 520,
    h = wide ? Math.min(height - 32, 920) : height,
    w = wide ? Math.min(440, (height - 32) * 0.5) : width,
    onboarding = s.route.startsWith("o");
  const bg = (
    {
      o0: slides[s.onboarding].scene,
      o1: "ball",
      o2: "gate",
      o3: "court2",
      o4: "hoop",
    } as Record<string, string>
  )[s.route];
  React.useEffect(() => {
    const listener = BackHandler.addEventListener("hardwareBackPress", () => {
      if (s.deleteOpen) {
        patch({ deleteOpen: false });
        return true;
      }
      if (["set", "cardb"].includes(s.route)) {
        go("me");
        return true;
      }
      if (!onboarding && s.route !== "home") {
        go("home");
        return true;
      }
      return false;
    });
    return () => listener.remove();
  }, [s.route, s.deleteOpen]);
  return (
    <View
      className="flex-1 items-center justify-center"
      style={{ backgroundColor: t.light ? "#eceef2" : t.bg }}
    >
      <StatusBar
        barStyle={t.light ? "dark-content" : "light-content"}
        backgroundColor="transparent"
      />
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={[
          { width: w, height: h, overflow: "hidden", backgroundColor: t.bg },
          wide && {
            borderRadius: 38,
            borderWidth: 2,
            borderColor: t.border,
            boxShadow: t.light
              ? "0 30px 80px rgba(0,0,0,.16)"
              : `0 0 70px ${rgba(t.accent, 0.18)}`,
          },
          gradient(
            t.light
              ? `radial-gradient(110% 34% at 100% 0,${rgba(t.accent, 0.1)},transparent 65%)`
              : `radial-gradient(110% 38% at 100% 0,${rgba(t.accent, 0.2)},transparent 65%),radial-gradient(90% 34% at 0 100%,${rgba(t.accent, 0.09)},transparent 65%)`,
          ),
        ]}
      >
        {bg && (
          <View
            style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
          >
            <Scene name={bg} overlay={false} style={{ flex: 1 }} />
            <View
              style={[
                StyleSheet.absoluteFill,
                gradient(
                  t.light
                    ? "linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.97) 72%)"
                    : "linear-gradient(180deg,rgba(5,5,6,.25),rgba(5,5,6,.95) 72%)",
                ),
              ]}
            />
          </View>
        )}
        <ScrollView
          key={s.route}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          style={{ flex: 1 }}
          contentContainerStyle={{
            flexGrow: 1,
            paddingTop: 18 + (wide ? 0 : insets.top),
            paddingHorizontal: 16,
            paddingBottom: 24 + (onboarding && !wide ? insets.bottom : 0),
          }}
        >
          {onboarding ? (
            <Onboarding />
          ) : s.route === "home" ? (
            <Home />
          ) : s.route === "club" ? (
            <ClubHub />
          ) : s.route === "cam" ? (
            <Camera />
          ) : s.route === "friends" ? (
            <Friends />
          ) : s.route === "me" ? (
            <Profile />
          ) : s.route === "set" ? (
            <Settings />
          ) : (
            <CardBuilder />
          )}
        </ScrollView>
        {!onboarding && <Navigation />}
        {s.deleteOpen && (
          <View
            accessibilityViewIsModal
            style={[
              StyleSheet.absoluteFill,
              {
                backgroundColor: "rgba(0,0,0,.7)",
                alignItems: "center",
                justifyContent: "center",
                padding: 24,
              },
            ]}
          >
            <Card
              style={{ borderColor: "#ef4444", borderRadius: 18, padding: 20 }}
            >
              <Label kind="h2">Delete account?</Label>
              <Label kind="muted" style={{ marginTop: 8, marginBottom: 16 }}>
                This permanently removes your card, stats, and uploaded footage.
                This can't be undone.
              </Label>
              <Button
                style={{ backgroundColor: "#ef4444", borderWidth: 0 }}
                textStyle={{ color: "#fff" }}
                onPress={() => update(() => initialState())}
              >
                Delete permanently
              </Button>
              <Button onPress={() => patch({ deleteOpen: false })}>
                Keep account
              </Button>
            </Card>
          </View>
        )}
      </KeyboardAvoidingView>
    </View>
  );
}
export default function App() {
  const [loaded, error] = useFonts(fonts);
  if (error) throw error;
  if (!loaded)
    return (
      <View
        className="flex-1 items-center justify-center"
        style={{ backgroundColor: "#fff" }}
      >
        <ActivityIndicator
          color="#FF6A00"
          accessibilityLabel="Loading NextRun fonts"
        />
      </View>
    );
  return (
    <SafeAreaProvider>
      <AppState>
        <Application />
      </AppState>
    </SafeAreaProvider>
  );
}
