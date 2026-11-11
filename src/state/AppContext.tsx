import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { AppState } from "react-native";
import * as Crypto from "expo-crypto";
import { soundPreferences, playSound, releaseSounds } from "./sound";
import { palettes } from "../theme/tokens";
import { readData, readAccount, persist } from "./storage";
import type { AppData, Route, Game, Notice } from "./types";
import {
  nrLevel,
  nrOvr,
  nrGameXp,
  nrYouLine,
  nrResult,
  nrEval,
  nrAutoTitle,
  NR_TRACKS,
  SPEC,
} from "./progression";
export const dayKey = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const questBank = [
  ["rec", "Record a session", "Start and stop a recording", 30, "camera"],
  ["card", "Tune your card", "Open the card builder", 20, "cardBuilder"],
  ["crew", "Check in with your Crew", "Visit the Crew tab", 20, "friends"],
  ["club", "Peek at the club feed", "Open Community", 20, "club"],
  ["ft", "Hit 25 free throws", "Self-report when done", 30],
  ["hnd", "10 min ball handling", "Self-report when done", 30],
  ["dfn", "Defensive slides, 3 × 30s", "Self-report when done", 30],
  ["str", "10 min mobility & stretching", "Self-report when done", 25],
  ["lay", "20 weak-hand layups", "Self-report when done", 30],
] as const;
function hash(s: string) {
  let h = 2166136261;
  for (const ch of s) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
export function makeQuest() {
  const day = dayKey(),
    h = hash(day),
    i = (h >>> 3) % 5;
  return {
    day,
    ids: [
      questBank[h % 4][0],
      questBank[4 + i][0],
      questBank[4 + ((i + 2) % 5)][0],
    ],
    done: [] as string[],
    claimed: false,
  };
}
export function initialData(): AppData {
  return {
    version: 1,
    handle: "",
    email: "",
    account: null,
    done: false,
    theme: "light",
    sex: "m",
    height: 178,
    heightUnit: "ft",
    weight: 75,
    weightUnit: "lbs",
    position: "",
    experience: "",
    location: "",
    privacy: "Club",
    card: {
      shape: "Standard",
      font: "Montserrat",
      c1: "#FF6A00",
      c2: "#0A0A0A",
      style: "Orange",
      pat: "Hex",
      frame: "Neon",
      name: "",
      num: "24",
      pos: "PG",
      shine: true,
      image: "",
      useCustom: false,
      removeBackground: true,
    },
    games: [],
    friends: [],
    messages: {},
    uploads: [],
    club: null,
    role: "Owner",
    equipped: null,
    notices: [],
    quest: makeQuest(),
    questXp: 0,
    streak: 0,
    lastClaim: "",
    sound: true,
    volume: 0.7,
  };
}
type Context = {
  data: AppData;
  setData: React.Dispatch<React.SetStateAction<AppData>>;
  route: Route;
  go: (r: Route) => void;
  ready: boolean;
  accountMode: "create" | "login";
  setAccountMode: (mode: "create" | "login") => void;
  editing: boolean;
  setEditing: (b: boolean) => void;
  historyTab: string;
  setHistoryTab: (s: string) => void;
  logging: boolean;
  setLogging: (b: boolean) => void;
  colors: typeof palettes.light;
  overall: number;
  level: ReturnType<typeof nrLevel>;
  title: string;
  notify: (title: string, body: string, route: Route) => void;
  completeQuest: (id: string) => void;
  logGame: (
    game: Omit<
      Game,
      | "xp"
      | "ovr"
      | "res"
      | "pts"
      | "ast"
      | "reb"
      | "fgm"
      | "fga"
      | "tpm"
      | "tpa"
    >,
  ) => void;
  reset: () => void;
  saveError: string;
};
const C = createContext<Context | null>(null);
export function AppProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<AppData>(initialData),
    [route, setRoute] = useState<Route>("intro"),
    [ready, setReady] = useState(false),
    [accountMode, setAccountMode] = useState<"create" | "login">("create"),
    [editing, setEditing] = useState(false),
    [historyTab, setHistoryTab] = useState("Sessions"),
    [logging, setLogging] = useState(false),
    [saveError, setSaveError] = useState("");
  const current = useRef(data);
  current.current = data;
  useEffect(
    () => soundPreferences(data.sound, data.volume),
    [data.sound, data.volume],
  );
  useEffect(() => () => releaseSounds(), []);
  useEffect(() => {
    let alive = true;
    Promise.all([readData(), readAccount()]).then(([saved, acct]) => {
      if (!alive) return;
      const d = { ...initialData(), ...saved };
      if (acct) d.account = acct;
      setAccountMode(d.account ? "login" : "create");
      if (d.quest.day !== dayKey()) d.quest = makeQuest();
      setData(d);
      setRoute(d.account ? "account" : d.done ? "home" : "intro");
      setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => {
      persist(data)
        .then(() => setSaveError(""))
        .catch(() =>
          setSaveError(
            "Could not save your changes. Keep the app open and try again.",
          ),
        );
    }, 250);
    return () => clearTimeout(t);
  }, [data, ready]);
  useEffect(() => {
    const sub = AppState.addEventListener("change", (s) => {
      if (s !== "active") {
        persist(current.current).catch(() =>
          setSaveError("Could not save your changes."),
        );
      } else
        setData((d) =>
          d.quest.day === dayKey() ? d : { ...d, quest: makeQuest() },
        );
    });
    return () => sub.remove();
  }, []);
  function completeQuest(id: string) {
    setData((d) => {
      if (!d.quest.ids.includes(id) || d.quest.done.includes(id)) return d;
      const q = questBank.find((x) => x[0] === id)!;
      return {
        ...d,
        questXp: d.questXp + Number(q[3]),
        quest: { ...d.quest, done: [...d.quest.done, id] },
      };
    });
  }
  function go(r: Route) {
    playSound("tick");
    setRoute(r);
    const q = { cardBuilder: "card", friends: "crew", club: "club" }[
      r as "cardBuilder" | "friends" | "club"
    ];
    if (q) completeQuest(q);
    if (r === "home" && !data.done) setData((d) => ({ ...d, done: true }));
  }
  function notify(title: string, body: string, r: Route) {
    setData((d) => ({
      ...d,
      notices: [
        { id: Crypto.randomUUID(), title, body, route: r, read: false },
        ...d.notices,
      ],
    }));
  }
  const xp = data.games.reduce((a, g) => a + g.xp, 0),
    level = nrLevel(xp),
    overall = nrOvr(level.lvl),
    ev = nrEval(data.games);
  let title = nrAutoTitle(ev).text;
  if (data.equipped) {
    const e = data.equipped;
    if (e.kind === "rookie") title = "Rookie";
    else if (e.kind === "rank" && ev.ranks[e.key])
      title = `${NR_TRACKS.find((t) => t.k === e.key)?.name} · Rank ${ev.ranks[e.key] === 10 ? "X" : ev.ranks[e.key]}`;
    else if (e.kind === "spec" && ev.spec[e.key])
      title = SPEC.find((s) => s.id === e.key)?.name || title;
  }
  function logGame(g: Parameters<Context["logGame"]>[0]) {
    playSound("win");
    const game = {
      ...g,
      ...nrYouLine(g),
      res: nrResult(g),
      xp: nrGameXp(g),
      ovr: overall,
    } as Game;
    setData((d) => ({
      ...d,
      games: [...d.games, game],
      notices: [
        {
          id: Crypto.randomUUID(),
          title: `${game.res === "W" ? "Win" : game.res === "L" ? "Loss" : "Tie"} logged · +${game.xp} PXP`,
          body: `${game.pts} pts, ${game.ast} ast, ${game.reb} reb.`,
          route: "history",
          read: false,
        },
        ...d.notices,
      ],
    }));
    setLogging(false);
  }
  function reset() {
    setData(initialData());
    setEditing(false);
    setLogging(false);
    setRoute("intro");
  }
  return (
    <C.Provider
      value={{
        data,
        setData,
        route,
        go,
        ready,
        accountMode,
        setAccountMode,
        editing,
        setEditing,
        historyTab,
        setHistoryTab,
        logging,
        setLogging,
        colors: palettes[data.theme],
        overall,
        level,
        title,
        notify,
        completeQuest,
        logGame,
        reset,
        saveError,
      }}
    >
      {children}
    </C.Provider>
  );
}
export function useApp() {
  const c = useContext(C);
  if (!c) throw Error("AppProvider missing");
  return c;
}
export const heightLabel = (cm: number, unit: string) =>
  unit === "cm"
    ? `${cm} cm`
    : `${Math.floor(Math.round(cm / 2.54) / 12)}'${Math.round(cm / 2.54) % 12}"`;
export const weightLabel = (kg: number, unit: string) =>
  `${Math.round(unit === "lbs" ? kg * 2.20462 : kg)} ${unit}`;
