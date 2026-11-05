// Rasterized directly from the supplied SVG paths. No substitute icon library.
import type { ImageSourcePropType } from "react-native";
export const artwork: Record<string, ImageSourcePropType> = {
  "home-accent": require("../../assets/artwork/home-accent.png"),
  "club-accent": require("../../assets/artwork/club-accent.png"),
  "cam-accent": require("../../assets/artwork/cam-accent.png"),
  "fr-accent": require("../../assets/artwork/fr-accent.png"),
  "me-accent": require("../../assets/artwork/me-accent.png"),
  "gear-accent": require("../../assets/artwork/gear-accent.png"),
  "bell-accent": require("../../assets/artwork/bell-accent.png"),
  "stat-accent": require("../../assets/artwork/stat-accent.png"),
  "arr-accent": require("../../assets/artwork/arr-accent.png"),
  "ball-accent": require("../../assets/artwork/ball-accent.png"),
  "bolt-accent": require("../../assets/artwork/bolt-accent.png"),
  "trophy-accent": require("../../assets/artwork/trophy-accent.png"),
  "flame-accent": require("../../assets/artwork/flame-accent.png"),
  "search-accent": require("../../assets/artwork/search-accent.png"),
  "mail-accent": require("../../assets/artwork/mail-accent.png"),
  art: require("../../assets/artwork/art.png"),
  run: require("../../assets/artwork/run.png"),
  "court-guide": require("../../assets/artwork/court-guide.png"),
  "court-pattern": require("../../assets/artwork/court-pattern.png"),
  silhouette: require("../../assets/artwork/silhouette.png"),
  avatar: require("../../assets/artwork/avatar.png"),
};

import { cardArtwork } from "./cardArtwork";
Object.assign(artwork, cardArtwork);
import { sceneArtwork } from "./sceneArtwork";
Object.assign(artwork, sceneArtwork);
