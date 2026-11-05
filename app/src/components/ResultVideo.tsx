import React from "react";
import { useVideoPlayer, VideoView } from "expo-video";
// Native (iOS/Android). The web build uses ResultVideo.web.tsx.
export function ResultVideo({ uri }: { uri: string }) {
  const player = useVideoPlayer(uri, (p) => {
    p.loop = true;
    p.play();
  });
  return (
    <VideoView
      player={player}
      nativeControls
      style={{ width: "100%", aspectRatio: 16 / 9, borderRadius: 14 }}
    />
  );
}
