import "./global.css";
import React, { useEffect, useRef } from "react";
import {
  View,
  ScrollView,
  StatusBar,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  BackHandler,
  Linking,
  Alert,
} from "react-native";
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import { useFonts } from "expo-font";
import { fonts } from "./src/theme/fonts";
import { AppProvider, useApp } from "./src/state/AppContext";
import { accent } from "./src/theme/tokens";
import { Icon, T } from "./src/components/ui";
import {
  Intro,
  Account,
  AthleteSetup,
  RecordingTips,
} from "./src/screens/Onboarding";
import { Home } from "./src/screens/Home";
import { Camera } from "./src/screens/Camera";
import { ClubScreen, FriendsScreen } from "./src/screens/Community";
import { Profile, CardBuilder } from "./src/screens/Profile";
import { History } from "./src/screens/History";
import { Settings } from "./src/screens/Settings";
import type { Route } from "./src/state/types";
const topRoutes: Route[] = [
  "home",
  "club",
  "camera",
  "friends",
  "profile",
  "cardBuilder",
  "history",
  "settings",
];
const navItems = [
  ["home", "Home", "home"],
  ["club", "Club Hub", "club"],
  ["cam", "", "camera"],
  ["fr", "Friends", "friends"],
  ["me", "Profile", "profile"],
] as const;
function Shell() {
  const { route, go, ready, data, setData, colors, saveError } = useApp(),
    insets = useSafeAreaInsets(),
    scroller = useRef<ScrollView>(null);
  useEffect(() => {
    scroller.current?.scrollTo({ y: 0, animated: false });
  }, [route]);
  useEffect(() => {
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (route === "intro" || route === "home") return false;
      const prev: Partial<Record<Route, Route>> = {
        account: "intro",
        athlete: "account",
        height: "athlete",
        weight: "height",
        gameProfile: "weight",
        recordTips: "gameProfile",
        settings: "profile",
        cardBuilder: "profile",
      };
      go(prev[route] || "home");
      return true;
    });
    return () => sub.remove();
  }, [route]);
  useEffect(() => {
    function invite(url: string) {
      try {
        if (url.startsWith("nextrun://friend?")) {
          const handle = new URL(url).searchParams.get("handle") || "";
          if (!/^@[a-z0-9_]{3,16}$/i.test(handle)) return;
          Alert.alert("Friend request", handle + " wants to be your friend.", [
            { text: "Not now", style: "cancel" },
            {
              text: "Add friend",
              onPress: () => {
                setData((d) => ({
                  ...d,
                  friends: d.friends.some((f) => f.name === handle)
                    ? d.friends
                    : [
                        ...d.friends,
                        {
                          name: handle,
                          date: new Date().toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          }),
                        },
                      ],
                }));
                go("friends");
              },
            },
          ]);
        } else if (url.startsWith("nextrun://join?")) {
          const j = JSON.parse(new URL(url).searchParams.get("data") || "{}");
          if (typeof j.n !== "string" || j.n.length > 120) return;
          Alert.alert("Club invite", j.n + " · invited by " + j.by, [
            { text: "Not now", style: "cancel" },
            {
              text: "Join club",
              onPress: () => {
                setData((d) => ({
                  ...d,
                  club: {
                    name: j.n,
                    university: String(j.s || "Independent"),
                    city: "",
                    uid: "",
                    c1: /^#[a-f\d]{6}$/i.test(j.c1) ? j.c1 : accent,
                    c2: /^#[a-f\d]{6}$/i.test(j.c2) ? j.c2 : "#0A0A0A",
                    members: [],
                    posts: [],
                  },
                  role: "Member",
                }));
                go("club");
              },
            },
          ]);
        }
      } catch {}
    }
    Linking.getInitialURL().then((u) => u && invite(u));
    const s = Linking.addEventListener("url", (e) => invite(e.url));
    return () => s.remove();
  }, []);
  if (!ready)
    return (
      <View style={{ flex: 1, justifyContent: "center" }}>
        <ActivityIndicator color={accent} />
      </View>
    );
  const onboarding = !topRoutes.includes(route);
  const content =
    route === "intro" ? (
      <Intro />
    ) : route === "account" ? (
      <Account />
    ) : ["athlete", "height", "weight", "gameProfile"].includes(route) ? (
      <AthleteSetup />
    ) : route === "recordTips" ? (
      <RecordingTips />
    ) : route === "home" ? (
      <Home />
    ) : route === "camera" ? (
      <Camera />
    ) : route === "club" ? (
      <ClubScreen />
    ) : route === "friends" ? (
      <FriendsScreen />
    ) : route === "profile" ? (
      <Profile />
    ) : route === "cardBuilder" ? (
      <CardBuilder />
    ) : route === "history" ? (
      <History />
    ) : (
      <Settings />
    );
  return (
    <View
      style={{
        flex: 1,
        backgroundColor: data.theme === "light" ? "#eceef2" : colors.bg,
        alignItems: "center",
      }}
    >
      <StatusBar
        barStyle={data.theme === "light" ? "dark-content" : "light-content"}
        backgroundColor={colors.bg}
      />
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{
          flex: 1,
          width: "100%",
          maxWidth: 480,
          backgroundColor: colors.bg,
          borderLeftWidth: Platform.OS === "web" ? 1 : 0,
          borderRightWidth: Platform.OS === "web" ? 1 : 0,
          borderColor: colors.border,
        }}
      >
        <View
          pointerEvents="none"
          style={{
            position: "absolute",
            right: 0,
            top: 0,
            width: "100%",
            height: 180,
            backgroundColor:
              data.theme === "light"
                ? "rgba(255,106,0,.025)"
                : "rgba(255,106,0,.06)",
          }}
        />
        <ScrollView
          ref={scroller}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{
            paddingTop: Math.max(18, insets.top),
            paddingHorizontal: 16,
            paddingBottom: 24,
            flexGrow: 1,
          }}
        >
          {content}
        </ScrollView>
        {!!saveError && (
          <T
            accessibilityRole="alert"
            style={{ color: "#ef4444", padding: 8, fontSize: 12 }}
          >
            {saveError}
          </T>
        )}
        {!onboarding && (
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "space-around",
              marginHorizontal: 10,
              marginBottom: Math.max(10, insets.bottom),
              paddingTop: 8,
              paddingBottom: 10,
              paddingHorizontal: 6,
              borderWidth: 1,
              borderColor: data.theme === "dark" ? colors.edge : colors.border,
              borderRadius: 28,
              backgroundColor: colors.nav,
              boxShadow:
                data.theme === "light"
                  ? "0 10px 28px rgba(18,20,30,.07)"
                  : "0 0 26px rgba(255,106,0,.10)",
            }}
          >
            {navItems.map(([icon, label, r]) => {
              const camera = r === "camera",
                active =
                  route === r ||
                  (r === "profile" &&
                    ["settings", "history", "cardBuilder"].includes(route));
              return (
                <Pressable
                  key={r}
                  accessibilityRole="tab"
                  accessibilityLabel={label || "Record"}
                  accessibilityState={{ selected: active }}
                  onPress={() => go(r)}
                  style={{
                    width: camera ? 58 : undefined,
                    minWidth: 52,
                    minHeight: camera ? 58 : 48,
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 3,
                    backgroundColor: camera ? accent : "transparent",
                    borderRadius: camera ? 58 : 0,
                    marginTop: camera ? -28 : 0,
                    borderWidth: camera ? 5 : 0,
                    borderColor: colors.bg,
                    boxShadow: camera
                      ? "0 0 18px rgba(255,106,0,.45)"
                      : undefined,
                  }}
                >
                  <Icon
                    name={icon}
                    color={camera ? "#fff" : active ? accent : colors.muted}
                  />
                  {!!label && (
                    <T
                      style={{
                        fontSize: 10,
                        fontFamily: "Inter-500",
                        color: active ? accent : colors.muted,
                      }}
                    >
                      {label}
                    </T>
                  )}
                </Pressable>
              );
            })}
          </View>
        )}
      </KeyboardAvoidingView>
    </View>
  );
}
export default function App() {
  const [loaded, error] = useFonts(fonts);
  if (error)
    return (
      <View style={{ padding: 24 }}>
        <StatusBar />
        <ActivityIndicator color={accent} />
      </View>
    );
  if (!loaded)
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator color={accent} />
      </View>
    );
  return (
    <SafeAreaProvider>
      <AppProvider>
        <Shell />
      </AppProvider>
    </SafeAreaProvider>
  );
}
