"use client";
import { useRef, useState, type DragEvent } from "react";
import { SurfaceCard } from "./surface-card";
export function VideoUploadCard({ artwork = "/figma/setup-upload-art.svg", light = false }: { artwork?: string; light?: boolean }) {
  const [video, setVideo] = useState("");
  const [fileError, setFileError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  function selectVideo(file?: File) {
    if (!file) return;
    if (!file.type.startsWith("video/")) { setFileError("Choose a video file."); return; }
    setFileError(""); setVideo(file.name);
  }
  function drop(event: DragEvent<HTMLElement>) { event.preventDefault(); selectVideo(event.dataTransfer.files[0]); }
  return (<SurfaceCard light={light} shadow={false} gradientAngle={159.98845521494368} aria-labelledby="upload-footage" onDragOver={event => event.preventDefault()} onDrop={drop} className={`h-[318.84px] ${light ? "" : "shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
        <h2 id="upload-footage" className={`absolute inset-x-[14px] top-[14px] text-center font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Upload game footage</h2>
        <div className="absolute inset-x-[14px] top-[41px] h-[190px] overflow-hidden rounded-[14px]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={artwork} alt="Basketball hoop and orange court lights" width={light ? 328 : 324} height={190} className="block max-w-none" />
        </div>
        <p aria-live="polite" className={`absolute inset-x-[14px] top-[237px] truncate text-center text-[13px] leading-[18.85px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{fileError || video || "Drag a game video here or choose a file."}</p>
        <input ref={fileInput} type="file" accept="video/*" aria-label="Game video" className="sr-only" onChange={event => selectVideo(event.target.files?.[0])} />
        <button type="button" onClick={() => fileInput.current?.click()} className={`absolute inset-x-[14px] top-[265.84px] h-[37px] rounded-full border px-[14px] py-[10px] text-center text-[12px] leading-[15px] font-semibold ${light ? "border-[#e7e8ec] bg-white text-[#0a0a0a]" : "border-white/[0.09] bg-[#0d0d0f] text-white"}`}>Choose video</button>
      </SurfaceCard>);
}
