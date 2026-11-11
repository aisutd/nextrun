const NR_CFG = {
  /* tier thresholds live here only */
  tiers: [
    {
      k: "D",
      min: 55,
      max: 69,
      blurb: "Lower-production profiles and role-player comparisons",
    },
    {
      k: "C",
      min: 70,
      max: 79,
      blurb: "Established rotation players and developing starters",
    },
    {
      k: "B",
      min: 80,
      max: 89,
      blurb: "High-level starters and standout specialists",
    },
    { k: "A", min: 90, max: 99, blurb: "Elite stars and all-time greats" },
  ],
  attrs: [
    { k: "ppg", label: "PPG", unit: "points per game", pct: false },
    { k: "apg", label: "APG", unit: "assists per game", pct: false },
    { k: "rpg", label: "RPG", unit: "rebounds per game", pct: false },
    { k: "tp", label: "3PT%", unit: "three-point percentage", pct: true },
    { k: "fg", label: "FG%", unit: "field-goal percentage", pct: true },
  ],
  weights: {
    ppg: 1,
    apg: 1,
    rpg: 1,
    tp: 1,
    fg: 1,
  } /* base weight per attribute */,
  focusBoost: 2 /* the user's strongest attribute counts this many times more */,
  minAttrs: 3 /* attributes both sides need before a match is allowed */,
  lowSampleGames: 100 /* career samples below this are flagged, not hidden */,
  requireVerified: true,
};
const nrTierOf = (ovr, cfg) => {
  cfg = cfg || NR_CFG;
  const T = cfg.tiers;
  if (ovr == null || isNaN(ovr)) return null;
  const o = Math.round(ovr);
  const t = T.find((t) => o >= t.min && o <= t.max);
  if (t) return { k: t.k, clamped: null, tier: t };
  if (o < T[0].min) return { k: T[0].k, clamped: "low", tier: T[0] };
  return { k: T[T.length - 1].k, clamped: "high", tier: T[T.length - 1] };
};
const nrBank = (roster, stats) =>
  roster.map((r) => {
    const s = stats[r.id] || {};
    const miss = NR_CFG.attrs.filter((a) => s[a.k] == null).map((a) => a.k);
    return Object.assign({}, r, s, {
      reqTier: r.tier,
      missing: miss,
      incomplete: s.status != "verified" || miss.length > 1,
      lowSample: s.g != null && s.g < NR_CFG.lowSampleGames,
      archetypes: nrArch(Object.assign({}, r, s)),
    });
  });
function nrArch(p) {
  const a = [];
  if (p.apg >= 6) a.push("Floor general");
  else if (p.apg >= 4 && ["PG", "SG"].includes(p.pos)) a.push("Playmaker");
  if (p.tp >= 38) a.push("Sharpshooter");
  if (p.ppg >= 24) a.push("Primary scorer");
  else if (p.ppg >= 18) a.push("Go-to scorer");
  if (p.rpg >= 9) a.push("Glass cleaner");
  if (p.fg >= 55 && p.rpg >= 6) a.push("Rim finisher");
  if (p.hcm && p.hcm <= 185) a.push("Small guard");
  if (!a.length)
    a.push(
      p.ppg < 10
        ? "Role player"
        : ["C", "PF"].includes(p.pos)
          ? "Frontcourt"
          : "Wing",
    );
  return a.slice(0, 3);
}
function nrStats(bank, cfg) {
  cfg = cfg || NR_CFG;
  const o = {};
  for (const a of cfg.attrs) {
    const v = bank.filter((p) => p[a.k] != null).map((p) => p[a.k]),
      m = v.reduce((x, y) => x + y, 0) / (v.length || 1),
      sd =
        Math.sqrt(
          v.reduce((x, y) => x + (y - m) * (y - m), 0) / (v.length || 1),
        ) || 1;
    o[a.k] = { m, sd };
  }
  return o;
}
/* the user's strongest attribute = highest z-score against the whole bank */
function nrStrongest(user, bs, cfg) {
  cfg = cfg || NR_CFG;
  let best = null;
  for (const a of cfg.attrs) {
    if (user[a.k] == null) continue;
    const z = (user[a.k] - bs[a.k].m) / bs[a.k].sd;
    if (!best || z > best.z) best = { k: a.k, z };
  }
  return best;
}
function nrMatch(user, ovr, bank, bs, cfg) {
  cfg = cfg || NR_CFG;
  const tier = nrTierOf(ovr, cfg);
  const have = cfg.attrs.filter((a) => user[a.k] != null);
  if (!tier) return { ok: false, reason: "No overall rating yet." };
  if (have.length < cfg.minAttrs)
    return {
      ok: false,
      tier,
      reason:
        "Not enough game stats: " +
        cfg.minAttrs +
        " of the 5 core stats are needed.",
    };
  const focus = nrStrongest(user, bs, cfg),
    pool = bank.filter(
      (p) =>
        p.reqTier == tier.k && (!cfg.requireVerified || p.status == "verified"),
    );
  const rows = [];
  for (const p of pool) {
    let sw = 0,
      sd = 0,
      n = 0;
    const parts = [];
    for (const a of have) {
      if (p[a.k] == null) continue;
      const w =
          cfg.weights[a.k] * (focus && focus.k == a.k ? cfg.focusBoost : 1),
        d = (user[a.k] - p[a.k]) / bs[a.k].sd;
      sw += w;
      sd += w * d * d;
      n++;
      parts.push({
        k: a.k,
        d: Math.abs(d),
        raw: user[a.k] - p[a.k],
        w,
        you: user[a.k],
        nba: p[a.k],
      });
    }
    if (n < cfg.minAttrs) continue;
    const dist = Math.sqrt(sd / sw);
    rows.push({
      id: p.id,
      name: p.name,
      dist,
      score: Math.round(100 / (1 + dist)),
      parts,
      n,
    });
  }
  rows.sort((x, y) => x.dist - y.dist || (x.id < y.id ? -1 : 1));
  if (!rows.length)
    return {
      ok: false,
      tier,
      focus,
      reason: "No verified players in " + tier.k + " tier have enough data.",
    };
  const best = rows[0];
  best.tie = rows.length > 1 && Math.abs(rows[1].dist - best.dist) < 1e-9;
  return { ok: true, tier, focus, best, list: rows, pool: pool.length };
}
const nrFmt = (k, v, cfg) =>
  v == null
    ? "N/A"
    : (cfg || NR_CFG).attrs.find((a) => a.k == k).pct
      ? v.toFixed(1) + "%"
      : v.toFixed(1);
function nrExplain(m, cfg) {
  cfg = cfg || NR_CFG;
  if (!m.ok) return m.reason;
  const L = (k) => cfg.attrs.find((a) => a.k == k).label,
    p = m.best.parts.slice().sort((x, y) => x.d * x.w - y.d * y.w);
  const near = p
      .slice(0, 2)
      .map(
        (x) =>
          L(x.k) + " (" + nrFmt(x.k, x.you) + " vs " + nrFmt(x.k, x.nba) + ")",
      ),
    far = p[p.length - 1];
  return (
    "Closest on " +
    near.join(" and ") +
    ". " +
    (m.focus
      ? "Your strongest stat is " +
        L(m.focus.k) +
        ", so it counts " +
        cfg.focusBoost +
        "x. "
      : "") +
    (far && p.length > 2 ? "Biggest gap: " + L(far.k) + "." : "")
  );
}
/* aggregate games -> per-game averages and shooting percentages (null when there were no attempts) */
function nrAvg(games) {
  const g = games.filter((x) => x && x.pts != null);
  if (!g.length) return null;
  const s = (k) => g.reduce((a, x) => a + (x[k] || 0), 0),
    n = g.length,
    fga = s("fga"),
    tpa = s("tpa");
  return {
    n,
    ppg: s("pts") / n,
    apg: s("ast") / n,
    rpg: s("reb") / n,
    fg: fga ? (s("fgm") / fga) * 100 : null,
    tp: tpa ? (s("tpm") / tpa) * 100 : null,
  };
}
const nrLine = (g) => ({
  ppg: g.pts,
  apg: g.ast,
  rpg: g.reb,
  fg: g.fga ? (g.fgm / g.fga) * 100 : null,
  tp: g.tpa ? (g.tpm / g.tpa) * 100 : null,
});
/* a player is unlocked when he is the #1 match of a logged game, using the rating the user had in that game */
function nrUnlocks(games, bank, bs) {
  const u = {};
  for (const g of games) {
    const m = nrMatch(nrLine(g), g.ovr, bank, bs);
    if (m.ok && !u[m.best.id])
      u[m.best.id] = { game: g.id, date: g.date, score: m.best.score };
  }
  return u;
}
/* what it takes to unlock a player */
function nrPlan(p, avg, ovr, bs, cfg) {
  cfg = cfg || NR_CFG;
  const t = cfg.tiers.find((t) => t.k == p.reqTier),
    cur = nrTierOf(ovr, cfg);
  let sig = null;
  for (const a of cfg.attrs) {
    if (p[a.k] == null) continue;
    const z = (p[a.k] - bs[a.k].m) / bs[a.k].sd;
    if (!sig || z > sig.z) sig = { k: a.k, z };
  }
  const rows = cfg.attrs.map((a) => ({
    k: a.k,
    label: a.label,
    target: p[a.k],
    you: avg ? avg[a.k] : null,
    gap: avg && avg[a.k] != null && p[a.k] != null ? avg[a.k] - p[a.k] : null,
  }));
  return {
    tier: t,
    needOvr:
      ovr < t.min
        ? t.min - Math.round(ovr)
        : ovr > t.max
          ? -(Math.round(ovr) - t.max)
          : 0,
    inTier: cur && cur.k == t.k,
    sig,
    rows,
  };
}

export {
  NR_CFG,
  nrTierOf,
  nrStats,
  nrStrongest,
  nrMatch,
  nrExplain,
  nrAvg,
  nrLine,
  nrUnlocks,
  nrPlan,
  nrFmt,
  nrArch,
};
