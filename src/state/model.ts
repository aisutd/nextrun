export type Route =
  | "o0"
  | "o1"
  | "o2"
  | "o3"
  | "o4"
  | "home"
  | "club"
  | "cam"
  | "friends"
  | "me"
  | "set"
  | "cardb";
export type Role = "Owner" | "Admin" | "Member";
export type Member = { handle: string; role: Role };
export type Post = { handle: string; role: Role; kind: string; text: string };
export type Club = {
  name: string;
  school: string;
  c1: string;
  c2: string;
  members: Member[];
  posts: Post[];
};
export type CardDesign = {
  shape: string;
  font: string;
  c1: string;
  c2: string;
  image: string;
  flip: boolean;
  pattern: string;
  frame: string;
  name: string;
  title: string;
  num: string;
  position: string;
  shine: boolean;
};
export type State = {
  route: Route;
  theme: "light" | "dark";
  accent: string;
  hue: number;
  handle: string;
  onboarding: number;
  tutorial: number;
  scanned: boolean;
  location: boolean;
  club: Club | null;
  inClub: boolean;
  role: Role;
  clubTab: string;
  hubTab: string;
  postKind: string;
  note: string;
  cameraTab: string;
  mode: string;
  recording: boolean;
  startedAt: number;
  uploadName: string;
  uploading: boolean;
  friendsTab: string;
  filter: string;
  chat: { me: boolean; text: string }[];
  feed: { name: string; text: string }[];
  roster: Record<string, string>;
  border: string;
  title: string;
  flipped: boolean;
  customCard: boolean;
  card: CardDesign;
  notifications: number;
  privacy: string;
  queueOpen: boolean;
  deleteOpen: boolean;
};
export function initialState(): State {
  return {
    route: "o0",
    theme: "light",
    accent: "#FF6A00",
    hue: 25,
    handle: "",
    onboarding: 0,
    tutorial: 0,
    scanned: false,
    location: false,
    club: null,
    inClub: false,
    role: "Owner",
    clubTab: "Feed",
    hubTab: "Leaderboard",
    postKind: "Post",
    note: "",
    cameraTab: "Live",
    mode: "Casual Pickup",
    recording: false,
    startedAt: 0,
    uploadName: "",
    uploading: false,
    friendsTab: "Active",
    filter: "All",
    chat: [{ me: false, text: "You up for a run tonight?" }],
    feed: [
      { name: "PlayerOne", text: "Game today was crazy! 🔥" },
      { name: "Hooper23", text: "Who is in for Saturday 5v5?" },
    ],
    roster: {
      PlayerOne: "A",
      Hooper23: "B",
      BallsLife: "",
      CourtVision: "",
      BucketsOnly: "",
    },
    border: "#FF6A00",
    title: "Rookie",
    flipped: false,
    customCard: false,
    card: {
      shape: "Standard",
      font: "Montserrat",
      c1: "#FF6A00",
      c2: "#0A0A0A",
      image: "",
      flip: false,
      pattern: "Court",
      frame: "Neon",
      name: "",
      title: "Rookie",
      num: "24",
      position: "PG",
      shine: true,
    },
    notifications: 2,
    privacy: "Club",
    queueOpen: false,
    deleteOpen: false,
  };
}
export const validHandle = (v: string) =>
  /^[a-z0-9_]{3,16}$/i.test(v.replace(/^@/, ""));
export const normalizeHandle = (v: string) => "@" + v.replace(/^@/, "");
export const canRemove = (role: Role, target: Role) =>
  role === "Owner" || (role === "Admin" && target === "Member");
export const formatTime = (s: number) =>
  String(Math.floor(s / 60)).padStart(2, "0") +
  ":" +
  String(s % 60).padStart(2, "0");
export function hueColor(h: number) {
  return (
    "#" +
    [0, 8, 4]
      .map((n) => {
        const k = (n + h / 30) % 12,
          v = 0.55 - 0.45 * Math.max(-1, Math.min(k - 3, 9 - k, 1));
        return Math.round(v * 255)
          .toString(16)
          .padStart(2, "0");
      })
      .join("")
  );
}
