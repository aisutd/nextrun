# NextRun — React Native scaffold

A native Expo project recreated from the supplied **NextRun1.0.html**. The app renders React Native views and uses NativeWind 4. It does not load the HTML into a WebView. No extra UI kit, icon library, navigation library, or animation library is used. Browser-only shadcn/ui components are not imported into native screens.

## Start on Windows

Install Node 20.19.4 or newer. Extract the ZIP, open PowerShell in the `nextrun` folder containing `package.json`, then run:

```powershell
npm.cmd ci
npm.cmd start
```

Open the project with a compatible Expo Go client or a development build. This project uses Expo SDK 54, React Native **0.81.5**, and React **19.1.0**. A different React Native version should not be installed manually.

For an Android emulator, start the emulator and press **a** in the Expo terminal. Building iOS locally requires macOS and Xcode. To generate native Android/iOS projects from the checked-in Expo configuration, run `npx expo prebuild`. Native build toolchains are not included in the ZIP.

The optional browser target can be started with `npm.cmd run web`; it keeps the HTML's centered 480px maximum app width. The primary implementation is mobile.

## Included screens

- Four intro slides, local account creation/login, athlete selection, height, weight, position, experience, and recording tips.
- Home, level/PXP progression, daily quests, progress, title goals, and notifications.
- Scouting camera simulation, file selection, upload presentation, and team assignment.
- University directory, custom clubs, local feed, member roles, leaderboard, club logos, and invitation links.
- Friends, local messages, and head-to-head records.
- Player card front/back, all seven source shapes, eight series, ten patterns, four frame choices, bundled fonts, and photo selection.
- Manual game logging, box scores, source MVP rules, XP, ranked/special titles, NBA mastery overview, player bank, filters, and comparisons.
- Light/dark mode, audio controls, local city/campus, privacy selection, JSON save export/import, reset, and delete confirmation.

## Shared components

`src/components/ui.tsx` contains the shared text styles, buttons, inputs, cards, chips, segments, badges, progress bars, toggles, sliders, icons, and layout primitives. `PlayerCard.tsx` shares the card front/back and title badges between profile and customization. `App.tsx` owns the mobile shell, safe areas, navigation, and deep-link prompts. Domain state and persistence live in `src/state`.

## Source fidelity and remaining differences

The final CSS overrides and JavaScript view overrides in the HTML are authoritative. Removed face-scan/location-permission screens and the earlier sample activity were not reintroduced. Colors, spacing, radii, font files, icons, source SVG scenes, title art, university logos, player data, progression formulas, and mastery formulas were extracted from the supplied file. Fonts are bundled locally. Source-rendered robot art and preset card backgrounds are shipped as PNG assets.

This is a complete runnable scaffold, **not a certified pixel-identical native port**. These differences remain:

- Browser canvas/WebGL scenes are source-rendered still frames. Native floating motion is present, but the original continuous 3D movement, canvas pointer tracking, CSS blur, and all CSS glow effects are not reproduced exactly.
- Preset series/shape/pattern backgrounds are reproduced from source artwork. Arbitrary custom hex colors update the card accents and saved options; the pre-rendered preset background does not fully regenerate in arbitrary colors.
- Uploaded card photos remain intact. The browser's automatic cutout brush/segmentation and adaptive face-avoidance algorithm have not been ported; photo placement and clipping can differ for nonrectangular shapes.
- Default robot thumbnails are bundled source renders rather than regenerated for every handle. Height scaling uses a native image transform. Native typography and shadows still need on-device visual QA.
- Title/level changes update immediately; the elaborate browser evolution cinematic and every reward-specific sound sequence are not all wired. Common button sounds and game-save sounds use audio rendered from the source synthesizer.
- Save files use a versioned native JSON envelope. Import/export of the HTML's separate encoded save-code format is not implemented.

The HTML itself provides a local account demo, local friend messages, local clubs and a simulated recording/processing flow. This scaffold preserves that scope: Google/Apple buttons open the local account form, recordings do not capture/analyze camera video, upload queues do not contact a processing service, and there is no multi-device backend. Policies in the HTML were labels without supplied policy documents.

Native credentials are salted SHA-256 hashes stored using SecureStore. App data is serialized to the app document directory; selected images are copied there so temporary picker paths do not expire. The browser target stores its local demo data in localStorage. App data is restored before saving starts, and writes are serialized.

## Checks

```powershell
npm.cmd run check
npx expo install --check
npx expo export --platform all
```

`npm run check` performs strict TypeScript checking and six regression tests for scoring, MVP ties, XP overflow/cap, fresh-player state, titles, and mastery tier/matching behavior. `package-lock.json` is included for reproducible installation. JavaScript export checks do not replace device testing or signed native builds.

## Project map

```text
App.tsx                 mobile shell and navigation
index.ts                Expo registration
src/components/         reusable native components
src/screens/            page implementations
src/state/              persistence, account state, progression, mastery, audio
src/theme/              exact source palette, typography, local asset registry
src/data/               extracted universities, players, design choices
assets/                 bundled fonts, icons, source-rendered artwork, audio
scripts/                asset registry and optional source extraction tools
tests/                  domain regression tests
docs/                   source inventory and implementation notes
```

## Optional artwork regeneration

All runtime assets are already included. `reference/NextRun1.0.html` is the unchanged uploaded reference and is never loaded by the app. To regenerate source-derived images/audio, install the separate build tools with `npm install --prefix scripts/tools`, then run `node scripts/extract-source.cjs` followed by `npm run assets:registry`. These tools use the source's own software renderer and SVG generators; they are not mobile dependencies. `docs/source-styles.css` preserves the complete source cascade for future visual comparisons.

The SDK 54 `expo-asset` version is explicitly pinned to prevent npm from satisfying the audio module’s broad peer dependency with a newer SDK’s asset runtime.
