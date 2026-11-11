const NR_PV = {
  reb: 1,
  ast: 2,
  base: 3,
  three: 4,
}; /* Player Value = REB + 2*AST + 3*(1PT and 2PT baskets) + 4*(3PT baskets) */
const NR_TRACKS = [
  {
    k: "allstar",
    name: "All Star",
    blurb: "Mastery of all NextRun stats",
    r: [
      { mvp: 1 },
      { mvp: 3 },
      { mvp: 5, pts: 25 },
      { mvp: 7, pts: 50, ast: 20, t3: 10 },
      { mvp: 10, pts: 65, ast: 30, reb: 20 },
      { mvp: 15, reb: 30 },
      { mvp: 20, ast: 50, t3: 25 },
      { mvp: 25, pts: 100, ast: 75, reb: 50, t3: 25 },
      { mvp: 30, pts: 250, ast: 100, reb: 100, t3: 50 },
      { mvp: 50 },
    ],
  },
  {
    k: "shooter",
    name: "Lethal Shooter",
    blurb: "Mastery of 3-pointers and shooting",
    r: [
      { t3: 3 },
      { t3: 7 },
      { t3: 12 },
      { t3: 16, t2: 5 },
      { t3: 20, t2: 10 },
      { t3: 25, t2: 20 },
      { t3: 40 },
      { t3: 60 },
      { t3: 75, t2: 35 },
      { t3: 100 },
    ],
  },
  {
    k: "catalyst",
    name: "Catalysts",
    blurb: "Mastery of scoring",
    r: [
      { pts: 10 },
      { pts: 20 },
      { pts: 25, t3: 2 },
      { pts: 40 },
      { pts: 50, t3: 10 },
      { pts: 65, t3: 15, ast: 15 },
      { pts: 90 },
      { pts: 100, t3: 22 },
      { pts: 150 },
      { pts: 200, t3: 30, ast: 50 },
    ],
  },
  {
    k: "playmaker",
    name: "Playmaker",
    blurb: "Mastery of assists",
    r: [
      { ast: 10, pts: 4 },
      { ast: 20, pts: 10 },
      { ast: 35 },
      { ast: 50 },
      { ast: 65, pts: 25 },
      { ast: 75, pts: 35, reb: 10 },
      { ast: 100 },
      { ast: 110, pts: 50, reb: 20 },
      { ast: 135, pts: 70 },
      { ast: 175, pts: 90, reb: 40 },
    ],
  },
  {
    k: "enforcer",
    name: "Enforcer",
    blurb: "Mastery of rebounds",
    r: [
      { reb: 5 },
      { reb: 10 },
      { reb: 20 },
      { reb: 25, pts: 10 },
      { reb: 35, pts: 20 },
      { reb: 50 },
      { reb: 60, pts: 40 },
      { reb: 75 },
      { reb: 110, pts: 60 },
      { reb: 150, pts: 75 },
    ],
  },
];
const NR_TOTL = {
  mvp: "MVPs",
  pts: "points",
  ast: "assists",
  reb: "rebounds",
  t3: "3-pointers",
  t2: "2-pointers",
};
const nrRankLabel = (r) => (r >= 10 ? "X" : String(r));
const NR_MINFRAUD = 5; /* shots needed before "Fraud" can apply */
const SPEC = [
  {
    id: "cone",
    name: "Traffic Cone",
    how: "Play a game for 15+ minutes with 0 points, 0 assists and 0 rebounds.",
    t: (c) => c.min >= 15 && c.p.pts == 0 && c.p.ast == 0 && c.p.reb == 0,
  },
  {
    id: "him",
    name: "“Him”",
    how: "Win MVP 5 games in a row.",
    streak: "mvp5",
  },
  {
    id: "binary",
    name: "The Binary",
    how: "Finish a game with points, assists and rebounds that only use the digits 1 and 0 (like 10 points, 10 assists, 1 rebound).",
    t: (c) =>
      [c.p.pts, c.p.ast, c.p.reb].every((v) => /^[01]+$/.test(String(v))) &&
      c.p.pts + c.p.ast + c.p.reb > 0,
  },
  {
    id: "prodigy",
    name: "Prodigy",
    how: "Win MVP in your very first NextRun game.",
    t: (c) => c.first && c.mvp,
  },
  {
    id: "unicorn",
    name: "Unicorn",
    how: "20 points, 20 assists and 20 rebounds in one game.",
    t: (c) => c.p.pts >= 20 && c.p.ast >= 20 && c.p.reb >= 20,
  },
  {
    id: "magnet",
    name: "Magnet",
    how: "15 rebounds in one game.",
    t: (c) => c.p.reb >= 15,
  },
  {
    id: "clean",
    name: "Clean Sheet",
    how: "Score at least 5 points without missing a single shot.",
    t: (c) => c.p.pts >= 5 && c.p.miss + c.p.miss3 == 0,
  },
  {
    id: "draymond",
    name: "The Draymond",
    how: "10+ rebounds, 10+ assists and fewer than 5 points.",
    t: (c) => c.p.reb >= 10 && c.p.ast >= 10 && c.p.pts < 5,
  },
  {
    id: "rodman",
    name: "The Rodman",
    how: "10+ rebounds while scoring exactly 0 points.",
    t: (c) => c.p.reb >= 10 && c.p.pts == 0,
  },
  {
    id: "fraud",
    name: "Fraud",
    how: "Shoot below 20% (needs at least " + NR_MINFRAUD + " shots).",
    t: (c) => c.att >= NR_MINFRAUD && c.made / c.att < 0.2,
  },
  {
    id: "team",
    name: "Team Sport",
    how: "5 assists without attempting a shot.",
    t: (c) => c.p.ast >= 5 && c.att == 0,
  },
  {
    id: "jack",
    name: "Jack of All Trades",
    how: "Points, assists and rebounds all above 8 in one game.",
    t: (c) => c.p.pts > 8 && c.p.ast > 8 && c.p.reb > 8,
  },
  {
    id: "master",
    name: "Master of One",
    how: "10+ in one of points, assists or rebounds with 0 in the other two.",
    t: (c) =>
      [c.p.pts, c.p.ast, c.p.reb].filter((v) => v == 0).length == 2 &&
      Math.max(c.p.pts, c.p.ast, c.p.reb) >= 10,
  },
  {
    id: "royal",
    name: "Royal Flush",
    how: "The same number of assists, rebounds, 3-pointers and 2-pointers (at least 1).",
    t: (c) =>
      c.p.ast > 0 &&
      c.p.ast == c.p.reb &&
      c.p.reb == c.p.n3 &&
      c.p.n3 == c.p.n2,
  },
  {
    id: "anchor",
    name: "The Anchor",
    how: "Score 0 points and finish with the best +/- on your team.",
    t: (c) =>
      c.p.pts == 0 &&
      c.p.pm != null &&
      c.mates.length > 0 &&
      c.mates.every((m) => m.pm != null && c.p.pm >= m.pm),
  },
  {
    id: "lebron",
    name: "LeBron",
    how: "25+ points, 7+ assists and 7+ rebounds in one game.",
    t: (c) => c.p.pts >= 25 && c.p.ast >= 7 && c.p.reb >= 7,
  },
  {
    id: "heat",
    name: "“He in the wrong heat!”",
    how: "Player Value 10+ above the second-highest player in the game.",
    t: (c) =>
      c.others.length > 0 &&
      c.val - Math.max(...c.others.map((o) => o.val)) >= 10,
  },
  {
    id: "flop",
    name: "Flop",
    how: "Player Value 10+ below every other player in the game.",
    t: (c) => c.others.length > 0 && c.others.every((o) => o.val - c.val >= 10),
  },
  {
    id: "gladiator",
    name: "Gladiator",
    how: "Play 10 matches in a row without a loss.",
    streak: "und10",
  },
];
const nrPts = (p) => p.n1 + 2 * p.n2 + 3 * p.n3,
  nrVal = (p) =>
    NR_PV.reb * p.reb +
    NR_PV.ast * p.ast +
    NR_PV.base * (p.n1 + p.n2) +
    NR_PV.three * p.n3;
const nrBlank = (n) => ({
  n,
  reb: 0,
  ast: 0,
  n1: 0,
  n2: 0,
  n3: 0,
  miss: 0,
  miss3: 0,
  foul: 0,
  pass: 0,
  pm: null,
});
const nrAll = (g) =>
  g.teams.flatMap((t, ti) =>
    t.map((p, pi) =>
      Object.assign({}, p, { team: ti, idx: pi, pts: nrPts(p), val: nrVal(p) }),
    ),
  );
/* MVP: highest Player Value; ties are broken by points, then assists, then rebounds; a remaining tie is a shared MVP */
function nrMvp(g) {
  const a = nrAll(g);
  if (!a.length) return [];
  const key = (p) => [p.val, p.pts, p.ast, p.reb];
  let best = [];
  for (const p of a) {
    if (!best.length) {
      best = [p];
      continue;
    }
    const c =
      key(p)
        .map((v, i) => v - key(best[0])[i])
        .find((d) => d != 0) || 0;
    if (c > 0) best = [p];
    else if (c == 0) best.push(p);
  }
  return best.map((p) => p.team + ":" + p.idx);
}
const nrScore = (g) => g.teams.map((t) => t.reduce((s, p) => s + nrPts(p), 0));
function nrResult(g) {
  const s = nrScore(g);
  return s[0] > s[1] ? "W" : s[0] < s[1] ? "L" : "T";
}
function nrYou(g) {
  const a = nrAll(g)[0];
  return a;
}
function nrEval(games) {
  const tot = { mvp: 0, pts: 0, ast: 0, reb: 0, t3: 0, t2: 0, games: 0 },
    spec = {};
  let mvpRun = 0,
    undRun = 0,
    xp = 0;
  games.forEach((g, gi) => {
    const all = nrAll(g),
      me = all.find((p) => p.team == 0 && p.idx == 0),
      mv = nrMvp(g),
      isMvp = mv.includes("0:0"),
      res = nrResult(g);
    tot.games++;
    tot.pts += me.pts;
    tot.ast += me.ast;
    tot.reb += me.reb;
    tot.t3 += me.n3;
    tot.t2 += me.n2;
    if (isMvp) tot.mvp++;
    mvpRun = isMvp ? mvpRun + 1 : 0;
    undRun = res == "L" ? 0 : undRun + 1;
    const others = all.filter((p) => !(p.team == 0 && p.idx == 0)),
      mates = all.filter((p) => p.team == 0 && p.idx > 0),
      made = me.n1 + me.n2 + me.n3,
      att = made + me.miss + me.miss3;
    const c = {
      p: me,
      val: me.val,
      mvp: isMvp,
      first: gi == 0,
      min: g.min || 0,
      made,
      att,
      others,
      mates,
    };
    for (const s of SPEC) {
      if (spec[s.id]) continue;
      const ok =
        s.streak == "mvp5"
          ? mvpRun >= 5
          : s.streak == "und10"
            ? undRun >= 10
            : s.t(c);
      if (ok) spec[s.id] = { gid: g.id, date: g.date };
    }
  });
  const ranks = {};
  for (const t of NR_TRACKS) {
    let r = 0;
    for (let i = 0; i < 10; i++) {
      if (Object.entries(t.r[i]).every(([k, v]) => tot[k] >= v)) r = i + 1;
    }
    ranks[t.k] = r;
  }
  return { tot, ranks, spec, mvpRun, undRun };
}
function nrNext(track, ev) {
  const r = ev.ranks[track.k];
  if (r >= 10) return null;
  const q = track.r[r];
  return {
    rank: r + 1,
    req: Object.entries(q).map(([k, v]) => ({
      k,
      have: Math.min(ev.tot[k], v),
      need: v,
      label: NR_TOTL[k],
    })),
  };
}
/* events produced by one new game: ranks that went up, new special titles */
function nrDiff(a, b) {
  const ev = [];
  for (const t of NR_TRACKS)
    if (b.ranks[t.k] > a.ranks[t.k])
      ev.push({
        type: "rank",
        key: t.k,
        name: t.name,
        from: a.ranks[t.k],
        to: b.ranks[t.k],
      });
  for (const s of SPEC)
    if (b.spec[s.id] && !a.spec[s.id])
      ev.push({ type: "spec", key: s.id, name: s.name });
  return ev;
}
/* auto-equipped title: highest ranked track, else newest special title, else Rookie */
function nrAutoTitle(ev) {
  let best = null;
  NR_TRACKS.forEach((t) => {
    const r = ev.ranks[t.k];
    if (r && (!best || r > best.r)) best = { k: t.k, r, name: t.name };
  });
  if (best)
    return {
      kind: "rank",
      key: best.k,
      text: best.name + " · Rank " + nrRankLabel(best.r),
    };
  const sp = Object.entries(ev.spec).sort((x, y) =>
    y[1].gid > x[1].gid ? 1 : -1,
  )[0];
  if (sp)
    return {
      kind: "spec",
      key: sp[0],
      text: SPEC.find((s) => s.id == sp[0]).name,
    };
  return { kind: "rookie", key: "rookie", text: "Rookie" };
}
/* Progression XP (PXP): every player starts at 55 OVR; each completed game earns PXP and every full bar is +1 OVR, permanently.
   PXP needed to go from OVR o to o+1 = 100 + 10 x (o - 55). Extra PXP carries over. Progression stops at 99. */
const NR_LV = {
  cap: 45,
  need: (l) => 100 + 10 * (l - 1),
  finish: 20,
  win: 20,
  pt: 7,
  ast: 5,
  reb: 3,
  foul: 2,
  pass: 0.5,
  passMax: 10,
};
function nrLevel(xp) {
  let l = 1,
    x = Math.max(0, Math.round(xp));
  while (l < NR_LV.cap && x >= NR_LV.need(l)) {
    x -= NR_LV.need(l);
    l++;
  }
  return {
    lvl: l,
    cur: l >= NR_LV.cap ? 0 : x,
    need: l >= NR_LV.cap ? 0 : NR_LV.need(l),
    pct: l >= NR_LV.cap ? 1 : x / NR_LV.need(l),
  };
}
const nrOvr = (l) => Math.min(99, 55 + Math.max(0, l - 1));
const nrGameXp = (g) => {
  const me = nrAll(g)[0];
  return Math.max(
    0,
    NR_LV.finish +
      (nrResult(g) == "W" ? NR_LV.win : 0) +
      NR_LV.pt * me.pts +
      NR_LV.ast * me.ast +
      NR_LV.reb * me.reb +
      Math.min(NR_LV.passMax, NR_LV.pass * (me.pass || 0)) -
      NR_LV.foul * (me.foul || 0),
  );
};
/* the user's line, in the shape the NBA mastery matcher expects */
const nrYouLine = (g) => {
  const m = nrAll(g)[0],
    fgm = m.n1 + m.n2 + m.n3;
  return {
    pts: m.pts,
    ast: m.ast,
    reb: m.reb,
    fgm,
    fga: fgm + m.miss + m.miss3,
    tpm: m.n3,
    tpa: m.n3 + m.miss3,
  };
};

export {
  NR_TRACKS,
  SPEC,
  nrPts,
  nrVal,
  nrBlank,
  nrAll,
  nrMvp,
  nrScore,
  nrResult,
  nrEval,
  nrNext,
  nrDiff,
  nrAutoTitle,
  nrLevel,
  nrOvr,
  nrGameXp,
  nrYouLine,
  NR_LV,
  nrRankLabel,
};
