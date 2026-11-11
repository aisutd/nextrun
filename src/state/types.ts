export type Route =
  | "intro"
  | "account"
  | "athlete"
  | "height"
  | "weight"
  | "gameProfile"
  | "recordTips"
  | "home"
  | "camera"
  | "club"
  | "friends"
  | "profile"
  | "cardBuilder"
  | "history"
  | "settings";
export type StatLine = {
  n: string;
  reb: number;
  ast: number;
  n1: number;
  n2: number;
  n3: number;
  miss: number;
  miss3: number;
  foul: number;
  pass: number;
  pm: number | null;
};
export type Game = {
  id: string;
  date: string;
  title: string;
  min: number;
  teams: StatLine[][];
  xp: number;
  ovr: number;
  res: string;
  pts: number;
  ast: number;
  reb: number;
  fgm: number;
  fga: number;
  tpm: number;
  tpa: number;
};
export type CardOptions = {
  shape: string;
  font: string;
  c1: string;
  c2: string;
  style: string;
  pat: string;
  frame: string;
  name: string;
  num: string;
  pos: string;
  shine: boolean;
  image: string;
  useCustom: boolean;
  removeBackground: boolean;
};
export type Friend = { name: string; date: string };
export type Club = {
  name: string;
  university: string;
  city: string;
  uid: string;
  c1: string;
  c2: string;
  logo?: string;
  members: { handle: string; role: string }[];
  posts: {
    id: string;
    handle: string;
    role: string;
    kind: string;
    text: string;
  }[];
};
export type Notice = {
  id: string;
  title: string;
  body: string;
  route: Route;
  read: boolean;
};
export type AppData = {
  version: 1;
  handle: string;
  email: string;
  account: { salt: string; hash: string } | null;
  done: boolean;
  theme: "light" | "dark";
  sex: "m" | "f";
  height: number;
  heightUnit: "ft" | "cm";
  weight: number;
  weightUnit: "lbs" | "kg";
  position: string;
  experience: string;
  location: string;
  privacy: string;
  card: CardOptions;
  games: Game[];
  friends: Friend[];
  messages: Record<string, string[]>;
  uploads: string[];
  club: Club | null;
  role: string;
  equipped: { kind: string; key: string } | null;
  notices: Notice[];
  quest: { day: string; ids: string[]; done: string[]; claimed: boolean };
  questXp: number;
  streak: number;
  lastClaim: string;
  sound: boolean;
  volume: number;
};
