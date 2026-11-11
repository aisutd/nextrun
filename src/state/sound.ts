import { createAudioPlayer, type AudioPlayer } from "expo-audio";
const clips = {
  tick: require("../../assets/audio/tick.wav"),
  select: require("../../assets/audio/select.wav"),
  back: require("../../assets/audio/back.wav"),
  toggleOn: require("../../assets/audio/toggleOn.wav"),
  toggleOff: require("../../assets/audio/toggleOff.wav"),
  flip: require("../../assets/audio/flip.wav"),
  win: require("../../assets/audio/win.wav"),
  level: require("../../assets/audio/level.wav"),
  claim: require("../../assets/audio/claim.wav"),
  quest: require("../../assets/audio/quest.wav"),
};
const players = new Map<string, AudioPlayer>();
let enabled = true,
  volume = 0.7;
export function soundPreferences(on: boolean, v: number) {
  enabled = on;
  volume = v;
}
export function playSound(name: keyof typeof clips = "tick") {
  if (!enabled || volume <= 0) return;
  try {
    let p = players.get(name);
    if (!p) {
      p = createAudioPlayer(clips[name]);
      players.set(name, p);
    }
    p.volume = Math.min(1, Math.pow(volume, 1.4) * 1.7);
    void p.seekTo(0);
    p.play();
  } catch {
    /* Sound availability must never prevent navigation. */
  }
}
export function releaseSounds() {
  players.forEach((p) => p.remove());
  players.clear();
}
