import type { Game, StatLine } from "./types";
export type GameInput = {
  id?: string;
  date?: string;
  min?: number;
  teams: StatLine[][];
};
export type Totals = {
  mvp: number;
  pts: number;
  ast: number;
  reb: number;
  t3: number;
  t2: number;
  games: number;
};
export type Evaluation = {
  tot: Totals;
  ranks: Record<string, number>;
  spec: Record<string, { gid: string; date: string }>;
  mvpRun: number;
  undRun: number;
};
export type Track = {
  k: string;
  name: string;
  blurb: string;
  r: Partial<Totals>[];
};
export const NR_TRACKS: Track[];
export const SPEC: { id: string; name: string; how: string }[];
export const NR_LV: {
  cap: number;
  need: (l: number) => number;
  finish: number;
  win: number;
  pt: number;
  ast: number;
  reb: number;
  foul: number;
  pass: number;
  passMax: number;
};
export function nrPts(p: StatLine): number;
export function nrVal(p: StatLine): number;
export function nrBlank(n: string): StatLine;
export function nrAll(
  g: GameInput,
): (StatLine & { team: number; idx: number; pts: number; val: number })[];
export function nrMvp(g: GameInput): string[];
export function nrScore(g: GameInput): number[];
export function nrResult(g: GameInput): string;
export function nrEval(g: GameInput[]): Evaluation;
export function nrNext(
  t: Track,
  e: Evaluation,
): {
  rank: number;
  req: { k: string; have: number; need: number; label: string }[];
} | null;
export function nrDiff(
  a: Evaluation,
  b: Evaluation,
): { type: string; key: string; name: string; from?: number; to?: number }[];
export function nrAutoTitle(e: Evaluation): {
  kind: string;
  key: string;
  text: string;
};
export function nrRankLabel(n: number): string;
export function nrLevel(xp: number): {
  lvl: number;
  cur: number;
  need: number;
  pct: number;
};
export function nrOvr(l: number): number;
export function nrGameXp(g: GameInput): number;
export function nrYouLine(g: GameInput): {
  pts: number;
  ast: number;
  reb: number;
  fgm: number;
  fga: number;
  tpm: number;
  tpa: number;
};
