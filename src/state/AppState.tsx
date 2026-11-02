import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";
import { AccessibilityInfo } from "react-native";
import { initialState, State, Route, CardDesign } from "./model";
type Context = {
  s: State;
  patch: (p: Partial<State>) => void;
  update: (f: (s: State) => State) => void;
  go: (r: Route) => void;
  card: (p: Partial<CardDesign>) => void;
  reducedMotion: boolean;
  upload: (name: string) => void;
};
const Context = createContext<Context | null>(null);
export function AppState({ children }: { children: React.ReactNode }) {
  const [s, set] = useState(initialState),
    [reducedMotion, reduce] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const patch = useCallback(
    (p: Partial<State>) => set((s) => ({ ...s, ...p })),
    [],
  );
  const update = useCallback((f: (s: State) => State) => set(f), []);
  const go = useCallback(
    (route: Route) => set((s) => ({ ...s, route, tutorial: 0 })),
    [],
  );
  const card = useCallback(
    (p: Partial<CardDesign>) =>
      set((s) => ({ ...s, card: { ...s.card, ...p } })),
    [],
  );
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(reduce);
    const sub = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      reduce,
    );
    return () => sub.remove();
  }, []);
  useEffect(() => {
    if (s.route !== "o0" || reducedMotion) return;
    const id = setInterval(
      () => set((s) => ({ ...s, onboarding: (s.onboarding + 1) % 3 })),
      6000,
    );
    return () => clearInterval(id);
  }, [s.route, reducedMotion]);
  useEffect(() => {
    if (s.route !== "o2" || s.scanned) return;
    const id = setTimeout(() => patch({ scanned: true }), 2800);
    return () => clearTimeout(id);
  }, [s.route, s.scanned, patch]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  const upload = useCallback(
    (name: string) => {
      patch({ uploadName: name, uploading: true });
      timers.current.push(setTimeout(() => patch({ uploading: false }), 1900));
    },
    [patch],
  );
  return (
    <Context.Provider
      value={{ s, patch, update, go, card, reducedMotion, upload }}
    >
      {children}
    </Context.Provider>
  );
}
export function useApp() {
  const c = useContext(Context);
  if (!c) throw Error("AppState provider is missing");
  return c;
}
