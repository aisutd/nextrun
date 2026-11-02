import { test } from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  validHandle,
  normalizeHandle,
  canRemove,
  formatTime,
  hueColor,
} from "../src/state/model.ts";
test("handle rules match source including optional @", () => {
  for (const h of ["abc", "@Player_24", "a".repeat(16)])
    assert.equal(validHandle(h), true);
  for (const h of ["ab", "a".repeat(17), "a-b", "ab c"])
    assert.equal(validHandle(h), false);
  assert.equal(normalizeHandle("@Jordan"), "@Jordan");
});
test("club moderation respects the role preview rules", () => {
  assert.equal(canRemove("Owner", "Admin"), true);
  assert.equal(canRemove("Admin", "Member"), true);
  assert.equal(canRemove("Admin", "Admin"), false);
  assert.equal(canRemove("Member", "Member"), false);
});
test("fresh sessions have independent nested state", () => {
  const a = initialState(),
    b = initialState();
  a.roster.PlayerOne = "B";
  a.card.title = "Sniper";
  a.chat.push({ me: true, text: "hi" });
  assert.equal(b.roster.PlayerOne, "A");
  assert.equal(b.card.title, "Rookie");
  assert.equal(b.chat.length, 1);
});
test("recording time and custom accent match source formulas", () => {
  assert.equal(formatTime(0), "00:00");
  assert.equal(formatTime(125), "02:05");
  assert.equal(hueColor(0), "#ff1a1a");
  assert.equal(hueColor(360), hueColor(0));
});
