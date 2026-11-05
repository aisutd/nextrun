import React from "react";
export function ResultVideo({ uri }: { uri: string }) {
  return React.createElement("video", {
    src: uri,
    controls: true,
    autoPlay: true,
    muted: true,
    loop: true,
    playsInline: true,
    style: { width: "100%", borderRadius: 14, backgroundColor: "#000" },
  });
}
