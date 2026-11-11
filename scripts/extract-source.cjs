const { JSDOM } = require("./tools/node_modules/jsdom");
const {
  createCanvas,
  Image,
  ImageData,
  GlobalFonts,
} = require("./tools/node_modules/@napi-rs/canvas");
const fs = require("fs"),
  path = require("path");
const proto = Object.getPrototypeOf(createCanvas(1, 1).getContext("2d"));
const originalDraw = proto.drawImage;
proto.drawImage = function (im, ...args) {
  return originalDraw.call(this, im._cv || im, ...args);
};
const src = fs.readFileSync(
  process.argv[2] || path.resolve(__dirname, "../reference/NextRun1.0.html"),
  "utf8",
);
const dom = new JSDOM('<html><body><div id="app"></div></body></html>', {
    url: "https://nextrun.local",
    runScripts: "outside-only",
  }),
  w = dom.window;
w.HTMLCanvasElement.prototype.getContext = function (type) {
  if (type != "2d") return null;
  if (!this._cv) this._cv = createCanvas(this.width || 300, this.height || 150);
  if (this._cv.width != this.width) this._cv.width = this.width;
  if (this._cv.height != this.height) this._cv.height = this.height;
  return this._cv.getContext("2d");
};
w.HTMLCanvasElement.prototype.toDataURL = function () {
  return this._cv.toDataURL();
};
w.Image = Image;
w.ImageData = ImageData;
w.matchMedia = () => ({ matches: true, addEventListener() {} });
w.requestAnimationFrame = () => 0;
w.setInterval = () => 0;
w.setTimeout = () => 0;
w.scrollTo = () => {};
let js = src
  .match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace(/SB\(\);R\(\);\s*$/, "");
js +=
  "\nwindow.NR={SFX,S,V,I,OB,UNI,NRB,NR_CFG,NR_STATS,STYLES,SH2,FNT,TIMG,PLIMG,SCN,CBG,CARDF,setPattern:v=>{CURPAT=v},CPATS,plBitmap,E3,LIVEDRAW,SC,OBS,sceneFrame,bust,look,DEF,NR_TRACKS,SPEC};";
js = js.replace("const api={ctx:", "const api={bus,ctx:");
w.eval(js);
const n = w.NR;
global.nr = n;
const root = path.resolve(__dirname, "..");
function json(file, obj) {
  fs.writeFileSync(root + "/" + file, JSON.stringify(obj, null, 2));
}
function asset(data, file) {
  if (!data) return "";
  const m = data.match(/^data:([^;,]+)(;base64)?,([\s\S]*)$/);
  if (!m) return data;
  const ext = m[1].includes("svg") ? "svg" : m[1].split("/")[1];
  const name = file + "." + ext;
  fs.writeFileSync(
    root + "/assets/" + name,
    m[2] ? Buffer.from(m[3], "base64") : decodeURIComponent(m[3]),
  );
  return name;
}
json(
  "src/data/universities.json",
  n.UNI.map((u) => ({
    id: u[0],
    name: u[1],
    short: u[2],
    city: u[3],
    c1: u[4],
    c2: u[5],
    asset: asset(u[6], "art/uni-" + u[0]),
  })),
);
json(
  "src/data/players.json",
  n.NRB.map((p) => ({ ...p, asset: "players/" + p.id + ".png" })),
);
for (const [k, v] of Object.entries(n.TIMG)) asset(v, "badges/" + k);
for (const p of n.NRB) {
  for (const col of [true, false]) {
    const cv = n.plBitmap(p, 340, 300, col);
    fs.writeFileSync(
      root + "/assets/players/" + p.id + (col ? "" : "-locked") + ".png",
      cv._cv.toBuffer("image/png"),
    );
  }
}
json("src/data/design.json", {
  onboarding: n.OB,
  styles: n.STYLES,
  shapes: n.SH2,
  fonts: n.FNT,
  patterns: n.CPATS,
  config: n.NR_CFG,
});
json("docs/source-inventory.json", {
  routes: Object.keys(n.V),
  stateKeys: Object.keys(n.S),
  css: src.match(/<style>([\s\S]*?)<\/style>/g).map((x) => x.length),
  embeddedImages: (src.match(/data:image/g) || []).length,
});
// Domain functions copied without modification from the source's documented pure-logic section.
const pure = js.slice(
  js.indexOf("const NR_PV="),
  js.indexOf("if(typeof module", js.indexOf("const NR_PV=")),
);
fs.writeFileSync(
  root + "/src/state/progression.js",
  pure +
    "\nexport {NR_TRACKS,SPEC,nrPts,nrVal,nrBlank,nrAll,nrMvp,nrScore,nrResult,nrEval,nrNext,nrDiff,nrAutoTitle,nrLevel,nrOvr,nrGameXp,nrYouLine,NR_LV,nrRankLabel};\n",
);
// Keep the original software renderer as a build-time tool, never a WebView.

async function main() {
  const sharp = require("./tools/node_modules/sharp");
  const { OfflineAudioContext } =
    await import("./tools/node_modules/node-web-audio-api/index.js");
  fs.mkdirSync(root + "/assets/audio", { recursive: true });
  const names = [
      "tick",
      "select",
      "back",
      "toggleOn",
      "toggleOff",
      "flip",
      "win",
      "level",
      "claim",
      "quest",
    ],
    dur = 6;
  const ac = new OfflineAudioContext(2, 44100 * dur * names.length, 44100),
    bus = n.SFX.bus(ac, 1);
  names.forEach((name, i) => n.SFX.P[name](ac, bus, i * dur + 0.01));
  const ab = await ac.startRendering(),
    channels = [ab.getChannelData(0), ab.getChannelData(1)];
  for (let ni = 0; ni < names.length; ni++) {
    const len = 44100 * dur,
      ch = 2,
      b = Buffer.alloc(44 + len * ch * 2);
    b.write("RIFF");
    b.writeUInt32LE(b.length - 8, 4);
    b.write("WAVEfmt ", 8);
    b.writeUInt32LE(16, 16);
    b.writeUInt16LE(1, 20);
    b.writeUInt16LE(ch, 22);
    b.writeUInt32LE(44100, 24);
    b.writeUInt32LE(44100 * ch * 2, 28);
    b.writeUInt16LE(ch * 2, 32);
    b.writeUInt16LE(16, 34);
    b.write("data", 36);
    b.writeUInt32LE(len * ch * 2, 40);
    for (let i = 0; i < len; i++)
      for (let j = 0; j < ch; j++)
        b.writeInt16LE(
          Math.round(
            Math.max(-1, Math.min(1, channels[j][ni * len + i])) * 32767,
          ),
          44 + (i * ch + j) * 2,
        );
    fs.writeFileSync(root + "/assets/audio/" + names[ni] + ".wav", b);
  }
  if (process.env.AUDIO_ONLY) return;
  for (const theme of ["light", "dark"]) {
    n.S.theme = theme;
    let dark = theme == "dark";
    for (const k of [
      "ball",
      "hoop",
      "court",
      "court2",
      "gate",
      "net",
      "city",
      "dunk",
      "arena",
    ]) {
      const s = n.SCN(k, !dark).replace(/var\(--or\)/g, "#FF6A00");
      await sharp(Buffer.from(s))
        .png()
        .toFile(root + "/assets/art/" + k + "-" + theme + ".png");
    }
    for (const [k, v] of Object.entries(n.I)) {
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="${dark ? "#ffffff" : "#0A0A0A"}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${v}</svg>`;
      await sharp(
        Buffer.from(
          svg.replace(/<[^>]+>/g, (t) => {
            const seen = new Set();
            return t.replace(/([\w:-]+)="[^"]*"/g, (a) => {
              const k = a.split("=")[0];
              if (seen.has(k)) return "";
              seen.add(k);
              return a;
            });
          }),
        ),
      )
        .png()
        .toFile(root + "/assets/icons/" + k + "-" + theme + ".png");
    }
    for (const kind of ["hero", "crew", "sexm", "sexf", "hgt", "wgt"]) {
      let [W, H] =
        kind == "hero" ? [260, 320] : kind == "crew" ? [360, 200] : [420, 560];
      const cv = createCanvas(W, H);
      n.LIVEDRAW[kind](cv.getContext("2d"), 0.5, { width: W, height: H });
      fs.writeFileSync(
        root + "/assets/art/" + kind + "-" + theme + ".png",
        cv.toBuffer("image/png"),
      );
    }
    for (let i = 0; i < n.OB.length; i++) {
      const cv = w.document.createElement("canvas");
      cv.width = 390;
      cv.height = 844;
      const c = cv.getContext("2d");
      n.SC[i](c, 390, 844, 0.5, dark);
      fs.writeFileSync(
        root + "/assets/art/intro-" + i + "-" + theme + ".png",
        cv._cv.toBuffer("image/png"),
      );
    }
    const cv = n.bust(n.look("you-"), 340, true);
    fs.writeFileSync(
      root + "/assets/art/avatar-" + theme + ".png",
      cv._cv.toBuffer("image/png"),
    );
  }
  for (const [k, v] of Object.entries(n.I)) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="#FF6A00" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${v}</svg>`;
    await sharp(
      Buffer.from(
        svg.replace(/<[^>]+>/g, (t) => {
          const seen = new Set();
          return t.replace(/([\w:-]+)="[^"]*"/g, (a) => {
            const k = a.split("=")[0];
            if (seen.has(k)) return "";
            seen.add(k);
            return a;
          });
        }),
      ),
    )
      .png()
      .toFile(root + "/assets/icons/" + k + "-accent.png");
  }
  for (const style of n.STYLES) {
    let s = n
      .CBG(style[1], style[2], style[3])
      .replace(
        "<svg ",
        '<svg xmlns="http://www.w3.org/2000/svg" width="448" height="620" ',
      );
    await sharp(Buffer.from(s))
      .png()
      .toFile(root + "/assets/cards/" + style[0] + ".png");
  }
  for (const st of n.STYLES) {
    for (const pat of n.CPATS) {
      n.setPattern(pat);
      for (const [shape, def] of Object.entries(n.SH2)) {
        let art = n.CBG(st[1], st[2], st[3]);
        const svg = art
          .replace(
            "<svg ",
            '<svg xmlns="http://www.w3.org/2000/svg" width="448" height="620" ',
          )
          .replace(
            "<defs>",
            `<defs><clipPath id="cardclip"><path d="${def.d}"/></clipPath>`,
          )
          .replace("</defs>", '</defs><g clip-path="url(#cardclip)">')
          .replace("</svg>", "</g></svg>");
        await sharp(
          Buffer.from(
            svg.replace(/<[^>]+>/g, (t) => {
              const seen = new Set();
              return t.replace(/([\w:-]+)="[^"]*"/g, (a) => {
                const k = a.split("=")[0];
                if (seen.has(k)) return "";
                seen.add(k);
                return a;
              });
            }),
          ),
        )
          .png()
          .toFile(
            root + "/assets/cards/" + st[0] + "-" + shape + "-" + pat + ".png",
          );
      }
    }
  }
  for (const [shape, def] of Object.entries(n.SH2)) {
    for (const [name, color] of [
      ["Neon", "#ffbc8c"],
      ["Double", "#ffffff"],
      ["Chrome", "#d8dbe2"],
    ]) {
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="448" height="620" viewBox="0 0 224 310"><path d="${def.d}" fill="none" stroke="${color}" stroke-width="5"/></svg>`;
      await sharp(
        Buffer.from(
          svg.replace(/<[^>]+>/g, (t) => {
            const seen = new Set();
            return t.replace(/([\w:-]+)="[^"]*"/g, (a) => {
              const k = a.split("=")[0];
              if (seen.has(k)) return "";
              seen.add(k);
              return a;
            });
          }),
        ),
      )
        .png()
        .toFile(root + "/assets/cards/frame-" + shape + "-" + name + ".png");
    }
  }
  console.log(
    "Extracted assets, final view markup, source data and pure progression logic.",
  );
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
