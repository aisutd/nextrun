// The static require calls let Metro package every asset for offline native use.
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
function walk(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .flatMap((e) =>
      e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)],
    );
}
const prefix = {
  icons: "icon-",
  badges: "badge-",
  players: "player-",
  cards: "card-",
};
const entries = walk(path.join(root, "assets"))
  .filter((p) => /\.(png|jpe?g)$/.test(p))
  .filter(
    (p) => !p.includes(path.sep + "players" + path.sep) || p.endsWith(".png"),
  )
  .map((p) => {
    const dir = path.basename(path.dirname(p)),
      name = path.basename(p, path.extname(p));
    return [
      (prefix[dir] || "") + name,
      path.relative(root, p).replaceAll(path.sep, "/"),
    ];
  })
  .sort((a, b) => a[0].localeCompare(b[0]));
fs.writeFileSync(
  path.join(root, "src/theme/assets.ts"),
  "import type {ImageSourcePropType} from 'react-native';\nexport const assets:Record<string,ImageSourcePropType> = {\n" +
    entries.map(([k, p]) => `  '${k}': require('../../${p}'),\n`).join("") +
    "};\n",
);
console.log(`Registered ${entries.length} local image assets.`);
