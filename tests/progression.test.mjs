import { test } from "node:test";
import assert from "node:assert/strict";
import {
  nrBlank,
  nrPts,
  nrVal,
  nrMvp,
  nrLevel,
  nrOvr,
  nrGameXp,
  nrEval,
  nrYouLine,
} from "../src/state/progression.js";
import {
  nrTierOf,
  nrMatch,
  nrStats,
  nrAvg,
  nrUnlocks,
} from "../src/state/mastery.js";
import fs from "node:fs";
const bank = JSON.parse(
  fs.readFileSync(new URL("../src/data/players.json", import.meta.url)),
);
const line = (n, s = {}) => ({ ...nrBlank(n), ...s });
test("source basket weights, player value and PXP stay distinct", () => {
  const p = line("You", { n1: 1, n2: 2, n3: 3, ast: 4, reb: 5 });
  assert.equal(nrPts(p), 14);
  assert.equal(nrVal(p), 34);
  const g = { teams: [[p], [line("Other")]], min: 20 };
  assert.equal(nrGameXp(g), 173);
  assert.deepEqual(nrYouLine(g), {
    pts: 14,
    ast: 4,
    reb: 5,
    fgm: 6,
    fga: 6,
    tpm: 3,
    tpa: 3,
  });
});
test("MVP uses value then points, assists, rebounds; exact ties share", () => {
  const a = line("A", { n2: 2 }),
    b = line("B", { n3: 1, ast: 1 });
  assert.deepEqual(nrMvp({ teams: [[a], [b]] }), ["0:0"]);
  assert.deepEqual(nrMvp({ teams: [[a], [{ ...a, n: "B" }]] }), ["0:0", "1:0"]);
});
test("levels retain overflow and cap at 99", () => {
  assert.equal(nrOvr(nrLevel(0).lvl), 55);
  assert.deepEqual(nrLevel(100), { lvl: 2, cur: 0, need: 110, pct: 0 });
  assert.equal(nrLevel(215).cur, 5);
  assert.equal(nrOvr(nrLevel(999999).lvl), 99);
});
test("fresh player has no awarded titles or fake games", () => {
  const e = nrEval([]);
  assert.equal(e.tot.games, 0);
  assert.equal(
    Object.values(e.ranks).reduce((a, b) => a + b, 0),
    0,
  );
  assert.equal(Object.keys(e.spec).length, 0);
  assert.equal(nrAvg([]), null);
});
test("first-game MVP unlocks Prodigy and ranked All Star", () => {
  const e = nrEval([
    {
      id: "g1",
      date: "Nov 10",
      min: 20,
      teams: [[line("You", { n2: 3, ast: 1 })], [line("Other")]],
    },
  ]);
  assert.ok(e.spec.prodigy);
  assert.equal(e.ranks.allstar, 1);
  assert.equal(e.tot.pts, 6);
});
test("mastery observes all tier boundaries and requires logged data", () => {
  for (const [ovr, tier] of [
    [55, "D"],
    [69, "D"],
    [70, "C"],
    [79, "C"],
    [80, "B"],
    [89, "B"],
    [90, "A"],
    [99, "A"],
  ])
    assert.equal(nrTierOf(ovr).k, tier);
  assert.deepEqual(nrUnlocks([], bank, nrStats(bank)), {});
  const p = bank.find((x) => x.reqTier === "D" && x.status === "verified");
  const match = nrMatch(p, 55, bank, nrStats(bank));
  assert.ok(match.ok);
  assert.equal(match.best.id, p.id);
  assert.equal(match.best.score, 100);
});
