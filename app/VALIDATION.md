# Validation and fidelity notes

## Source review

The complete supplied HTML was read before implementation: all appended CSS overrides, JavaScript view overrides, inline SVG, event handlers, timers, and data. Its final overrides were treated as authoritative, rather than the earlier versions of the same views.

The source has 12 route states: five onboarding stages, Home, Club Hub, Camera, Friends, Profile, Settings, and Custom Card. Club Hub includes four default tabs and a separate role-based club workspace. Camera has three tabs and three session modes. Friends has three tabs and four filters. Card Builder supports seven shapes, seven patterns, four frames, nine typefaces, seven palettes, custom colors, and custom identity fields.

Rendered source DOM inspection covered 1,023 nested elements across the 12 route defaults, including computed layout and typography. The external Google Fonts stylesheet did not load in the isolated inspection browser, so visual inspection explicitly loaded the exact declared font families from the bundled font files. Screenshots were also stabilized with reduced motion. The original HTML is retained byte-for-byte in `reference/NextRun-Upgrade.html`.

## Completed checks

- `npm ci` / dependency installation, with the lockfile included.
- Expo SDK dependency compatibility check.
- TypeScript strict checking, including unused-local and unused-parameter checking.
- Four focused tests covering handle validation, club moderation rules, independent session resets, and timer/accent formulas.
- Expo production JavaScript/asset export for **iOS, Android, and web**.
- Browser interaction tests against the exported React Native Web build: full onboarding; every navigation tab; card shape, pattern, frame and identity changes; adopting/flipping a custom card; sending a message; assigning roster teams; recording start/stop; processing library; creating a club; posting; inviting/promoting a member; switching to Member role; changing theme/accent; canceling and confirming deletion; and desktop frame layout.
- Visual comparisons of onboarding, Home, Club Hub, Camera, Friends, Profile, Settings, and Card Builder, followed by corrections to image sizing, scene cropping, source spacing, progress rings, translucent session surfaces, and card layers.

Source SVG scenes are rendered as local raster assets. Color-dependent scenes are split into an opaque base plus a tintable alpha layer, allowing the source's arbitrary hue control to work. Reconstruction checks on three representative orange scenes measured average per-channel errors below 0.31 on a 0–255 scale. Shape, pattern, gradient, and frame layers for custom cards were captured directly from the source's CSS rendering. Source progress-ring geometry and all original icon paths were preserved in the extracted artwork.

## Limits and remaining visual differences

This is a runnable native frontend scaffold, not a device-certified pixel-equality result. iOS and Android **bundles were compiled**, but no native simulator/device was available for runtime testing. In particular, React Native's experimental gradient support, native font baselines, Android shadow support, safe areas and file-picker permissions still require target-device checks.

Some CSS effects do not have an exact counterpart among the permitted React Native primitives:

- Color inputs use a swatch with precise hex editing, and dropdowns open a native selection sheet.
- Backdrop blur is represented by translucent native surfaces. Text rasterization and shadow falloff may differ by operating system.
- On native platforms, jersey-number outlines use layered native text; web uses the original stroke treatment.
- Card background/pattern/frame shapes use the exact source masks. Dynamic text and uploaded portraits are separate native views; the source's CSS clipping and portrait fade are not fully reproduced for every nonrectangular shape.
- Card flip, gentle hanging motion, onboarding rotation and scan sweep are native animations. The source's pointer-driven 3D tilt, moving holo shimmer, decorative floating glows, dunk animation, and every original animation curve are not fully reproduced. Reduced-motion preferences are respected.

The source itself simulates authentication, face scanning, location discovery, recording and analytics. Those demo behaviors remain simulations; local selfie/video selection works through Expo platform pickers. No backend, remote upload, real invitations, production role authorization or account service is claimed.
