"use client";
import { useState } from "react";
import { ScreenShell } from "./screen-shell";
import { DashboardNavigation } from "./dashboard-navigation";
import { CameraHeader } from "./camera-header";
import { CameraTabs } from "./camera-tabs";
import { CameraRoster } from "./camera-roster";

const modes = [{ label: "Casual Pickup", width: 112.45 }, { label: "Tournament Game", width: 137.25 }, { label: "Solo Drills", width: 88.3 }];
const pill = "flex h-[37px] shrink-0 items-center justify-center rounded-full border px-[14px] py-[10px] text-[12px] leading-[15px] font-semibold";
const selectedPill = "border-blaze bg-linear-to-b from-[#ff7f24] to-blaze text-white shadow-[0_0_18px_rgba(255,106,0,0.5)]";

export function CameraLive({ light = false }: { light?: boolean }) {
  const [mode, setMode] = useState("Casual Pickup");
  return <ScreenShell light={light} label="Scouting camera live" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"><div className="relative min-h-[840px] w-full">
      <CameraHeader light={light} />
      <CameraTabs active="live" light={light} />
      <div role="group" aria-label="Session mode" className="absolute inset-x-[10px] top-[112px] flex h-[55px] gap-[8px] overflow-x-auto rounded-[12px] px-[6px] pt-[6px] pb-[12px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">{modes.map(item => <button key={item.label} type="button" aria-pressed={mode === item.label} onClick={() => setMode(item.label)} style={{ width: item.width + (light ? 1.33 : 0) }} className={`${pill} ${mode === item.label ? light ? "border-blaze bg-linear-to-b from-[#ff7f24] to-blaze text-white shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : selectedPill : light ? "border-[#e7e8ec] bg-white text-[#5b6270]" : "border-white/[0.09] bg-[#0d0d0f] text-muted"}`}>{item.label}</button>)}</div>
      <section aria-label="Court alignment preview" className={`absolute inset-x-[16px] top-[167px] h-[238px] overflow-hidden rounded-[24px] border bg-linear-to-b ${light ? "border-blaze/45 from-white to-[#f6ece2] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-blaze/[0.38] from-[#1a1008] to-[#3a1f0a] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={light ? "/figma/camera-light-court.svg" : "/figma/camera-court-art.svg"} alt="" width={light ? 358 : 354} height={238} className="absolute -top-px -left-px max-w-none" /><div className={`absolute inset-0 bg-linear-to-b ${light ? "from-white/5 to-[#f4f3f0]/80" : "from-black/10 to-black/70"}`} />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={light ? "/figma/camera-light-guide.svg" : "/figma/camera-court-guide.svg"} alt="Orange court alignment guide" width={light ? 356 : 352} height={236} className="absolute top-0 left-0 max-w-none" />
        {["top-[12px] left-[12px] border-t-2 border-l-2 rounded-tl-[9px]", "top-[12px] right-[12px] border-t-2 border-r-2 rounded-tr-[9px]", "bottom-[12px] left-[12px] border-b-2 border-l-2 rounded-bl-[9px]", "bottom-[12px] right-[12px] border-b-2 border-r-2 rounded-br-[9px]"].map(corner => <span key={corner} aria-hidden="true" className={`absolute size-[24px] border-blaze drop-shadow-[0_0_2px_rgba(255,106,0,0.7)] ${corner}`} />)}
        <span className="absolute top-[14px] right-[44px] rounded-[20px] border border-blaze/[0.35] bg-black px-[8px] py-[3px] font-mono text-[10px] leading-[13px] font-semibold text-white">READY 1080p</span>
        <p className="absolute bottom-[16px] left-[44px] font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] whitespace-nowrap text-blaze uppercase">Align court lines to guide</p>
        <div className="pointer-events-none absolute inset-0 rounded-[inherit] shadow-[inset_0_0_40px_1px_rgba(255,106,0,0.12)]" />
      </section>
      <div className={light ? "absolute top-[417px] inset-x-[16px]" : "absolute top-[416.83px] right-[16.32px] left-[15.68px]"}><CameraRoster light={light} /></div>
    </div></div>
    <DashboardNavigation active="record" light={light} className={light ? "!bottom-[-2px]" : "translate-x-[-0.32px] translate-y-[-1.17px]"} />
  </ScreenShell>;
}
