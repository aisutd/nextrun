export type CoreStats = Record<string, number | null>;
export type Tier = { k: string; min: number; max: number; blurb: string };
export type MatchEntry = {
  id: string;
  name: string;
  score: number;
  parts: { k: string; d: number; w: number }[];
};
export type Match =
  | {
      ok: true;
      best: MatchEntry;
      list: MatchEntry[];
      tier: { k: string };
      focus?: { k: string };
    }
  | { ok: false; reason: string };
export const NR_CFG: {
  tiers: Tier[];
  attrs: { k: string; label: string; unit: string; pct: boolean }[];
};
export function nrTierOf(ovr: number): {
  k: string;
  tier: Tier;
  clamped: string | null;
};
export function nrStats(
  bank: unknown[],
): Record<string, { m: number; sd: number }>;
export function nrMatch(
  user: CoreStats,
  ovr: number,
  bank: unknown[],
  stats: unknown,
): Match;
export function nrExplain(match: Match): string;
export function nrAvg(games: unknown[]): (CoreStats & { n: number }) | null;
export function nrUnlocks(
  games: unknown[],
  bank: unknown[],
  stats: unknown,
): Record<string, { game: string; date: string; score: number }>;
export function nrPlan(
  p: unknown,
  avg: unknown,
  ovr: number,
  stats: unknown,
): unknown;
export function nrLine(g: unknown): CoreStats;
