"use client";

import Link from "next/link";
import { useRef, useState, type CSSProperties, type ReactNode } from "react";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { PlayerCard } from "./player-card";
import { PrimaryButton } from "./primary-button";
import { DashboardNavigation } from "./dashboard-navigation";

const inputClasses = "h-[46px] min-w-0 rounded-[14px] border border-[var(--custom-border)] bg-[var(--custom-input-bg)] px-[13px] text-[15px] leading-[18px] font-medium text-[var(--custom-text)] placeholder:text-[#777] focus-visible:outline-2 focus-visible:outline-blaze";
const titleOptions = ["Rookie", "Sniper", "Floor General", "Glass Cleaner", "Lockdown", "Clutch Gene"];
const fontOptions = ["Montserrat", "Bebas Neue", "Orbitron", "Rajdhani", "Oswald", "Russo One", "Playfair Display", "Inter", "JetBrains Mono"];
const palettes = [["#FF6A00", "#0A0A0A"], ["#00E5FF", "#0A0A2A"], ["#B6FF00", "#0A1A00"], ["#2E7BFF", "#050A24"], ["#FF2BD6", "#1A0020"], ["#FFD34E", "#2A1A00"], ["#E5E7EB", "#1F2937"]];

function Heading({ children, light = false }: { children: ReactNode; light?: boolean }) {
  return <h2 className={`relative w-full font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] ${light ? "text-[#0a0a0a]" : "text-white"} italic`}>{children}</h2>;
}

/** Measured horizontal option rails, shared by each card customization field. */
function OptionRail({ label, options, positions, widths, value, onChange, fonts = false, light = false }: { label: string; options: string[]; positions: number[]; widths: number[]; value: string; onChange: (value: string) => void; fonts?: boolean; light?: boolean }) {
  return <div role="group" aria-label={label} className={`relative ${light ? "w-[340px]" : "w-[336px]"} max-w-[calc(100%+12px)] shrink-0 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${fonts ? "h-[59px]" : "h-[57px]"}`}>
    {options.map((option, index) => <button key={option} type="button" aria-pressed={value === option} onClick={() => onChange(option)} style={{ left: positions[index], width: widths[index], fontFamily: fonts ? option : undefined, height: fonts ? [39,38,39,39,40,39,39,39,39][index] : 37 }} className={`absolute top-[8px] flex items-center justify-center rounded-full border text-[12px] leading-[15px] whitespace-nowrap ${light ? "text-[#0a0a0a]" : "text-white"} ${fonts && ["Bebas Neue", "Russo One"].includes(option) ? "font-normal" : "font-semibold"} ${value === option ? light ? "border-blaze bg-blaze/10 shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "border-blaze bg-blaze/10 shadow-[0_0_18px_rgba(255,106,0,0.5)]" : light ? "border-[#e7e8ec] bg-white" : "border-white/[0.09] bg-[#0d0d0f]"}`}>{option}</button>)}
  </div>;
}

export function CustomPlayerCard({ light = false }: { light?: boolean }) {
  const selfieInput = useRef<HTMLInputElement>(null);
  const [selfie, setSelfie] = useState("");
  const [selfieError, setSelfieError] = useState("");
  const [name, setName] = useState("");
  const [title, setTitle] = useState("Rookie");
  const [number, setNumber] = useState("24");
  const [position, setPosition] = useState("PG");
  const [shape, setShape] = useState("Standard");
  const [design, setDesign] = useState("Court");
  const [frame, setFrame] = useState("Neon");
  const [typeface, setTypeface] = useState("Montserrat");
  const [primary, setPrimary] = useState("#ff6a00");
  const [secondary, setSecondary] = useState("#0a0a0a");
  const [holo, setHolo] = useState(true);
  const [saved, setSaved] = useState(false);
  function saveDraft() {
    sessionStorage.setItem("nextrun.customPlayerCardDraft", JSON.stringify({ name, title, number, position, shape, design, frame, typeface, primary, secondary, holo, selfie }));
    setSaved(true);
  }
  return <ScreenShell light={light} label={light ? "Light custom player card" : "Custom player card"} backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div style={{ "--custom-text": light ? "#0a0a0a" : "#fff", "--custom-muted": light ? "#5b6270" : "#9ca3af", "--custom-input-bg": light ? "#f2f3f5" : "#17171b", "--custom-border": light ? "#e7e8ec" : "rgba(255,255,255,0.09)" } as CSSProperties} className={`relative flex w-full flex-col items-center gap-[10px] px-[16px] pb-[110px] ${light ? "pt-[44px]" : "-left-[0.32px] pt-[44.83px]"}`}>
        <header className="flex h-[36px] w-full shrink-0 items-center gap-[10px]"><Link href={light ? "/profile/light" : "/profile"} aria-label="Back to Profile" className={`flex h-[36px] w-[40px] shrink-0 items-center justify-center rounded-[16px] border text-[15px] leading-[18px] font-semibold ${light ? "border-[#e7e8ec] bg-white text-[#0a0a0a] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-white/[0.09] bg-[#0d0d0f] text-white shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>‹</Link><h1 className="font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] text-[var(--custom-text)] italic">Custom card</h1></header>
        <PlayerCard initialAlternate light={light} />
        {light && <>
          <p className="h-[19px] w-full pt-[4px] text-center font-mono text-[11px] leading-[15px] text-[#5b6270]">Tap the card to flip</p>
          <input ref={selfieInput} aria-label="Selfie image" type="file" accept="image/*" className="sr-only" onChange={event => { const file = event.target.files?.[0]; if (!file) return; if (!file.type.startsWith("image/")) { setSelfieError("Choose an image file"); return; } setSelfie(file.name); setSelfieError(""); }} />
          <PrimaryButton type="button" onClick={() => selfieInput.current?.click()} className="!h-[50px] shrink-0 !pt-[16px] !shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_6px_18px_rgba(255,106,0,0.35)]">Upload selfie</PrimaryButton>
          {(selfie || selfieError) && <p role="status" className="w-full text-[13px] leading-[19px] text-[#5b6270]">{selfieError || selfie}</p>}
        </>}
        <SurfaceCard light={light} aria-label="Identity" gradientAngle={159.9727830381826} className="h-[281px] shrink-0">
          <div className="absolute inset-x-[14px] top-[14px]"><Heading light={light}>Identity</Heading></div>
          <input aria-label="Player name" placeholder="Player name" value={name} onChange={event => setName(event.target.value)} className={`absolute inset-x-[14px] top-[43px] ${inputClasses}`} />
          <input aria-label="Player title" value={title} onChange={event => setTitle(event.target.value)} className={`absolute inset-x-[14px] top-[100px] ${inputClasses}`} />
          <div className="absolute inset-x-[8px] top-[149px]"><OptionRail light={light} label="Title presets" options={titleOptions} positions={[6,83.02,158.66,274.47,392.98,490.67]} widths={[70,68,108,111,90,102]} value={title} onChange={setTitle} /></div>
          <div className="absolute inset-x-[14px] top-[216px] flex h-[47px] items-center gap-[10px]">
            <input aria-label="Jersey number" inputMode="numeric" value={number} onChange={event => setNumber(event.target.value)} className={`flex-1 ${inputClasses}`} />
            <input aria-label="Position" value={position} onChange={event => setPosition(event.target.value)} className={`!h-[47px] flex-1 !pl-[17px] !pr-[29px] ${inputClasses}`} />
          </div>
        </SurfaceCard>
        <SurfaceCard light={light} aria-label="Card style" gradientAngle={160.04381649706772} shadowTop={1} className="flex h-[305px] shrink-0 flex-col items-center gap-[8px] px-[14px] pt-[16px] pb-[14px]">
          <Heading light={light}>Shape</Heading>
          <OptionRail light={light} label="Shape" options={["Standard","Rounded","Arch","Shield","Tech","Hex","Slant"]} positions={[6,96.7,186.45,252.03,326.06,392.48,453.11]} widths={[84,82,58,67,59,53,60]} value={shape} onChange={setShape} />
          <div className="w-full pt-[4px]"><Heading light={light}>Design</Heading></div>
          <OptionRail light={light} label="Design" options={["Court","Lines","Dots","Burst","Grid","Carbon","None"]} positions={[6,76.72,145.69,210.39,279.25,341.72,422.55]} widths={[64,61,58,62,55,73,61]} value={design} onChange={setDesign} />
          <div className="w-full pt-[4px]"><Heading light={light}>Frame</Heading></div>
          <OptionRail light={light} label="Frame" options={["Neon","Double","Chrome","None"]} positions={[6,75,155,239]} widths={[61,72,76,61]} value={frame} onChange={setFrame} />
        </SurfaceCard>
        <SurfaceCard light={light} aria-label="Typeface and colors" gradientAngle={159.9750930979749} shadow={false} className="flex h-[286px] shrink-0 flex-col items-center gap-[8px] px-[14px] pt-[16px] pb-[14px]">
          <Heading light={light}>Typeface</Heading>
          <OptionRail light={light} label="Typeface" options={fontOptions} positions={[6,112.03,193.94,287.05,368.06,440.05,542.97,668.33,732.98]} widths={[99,74,85,73,64,95,117,57,131]} value={typeface} onChange={setTypeface} fonts />
          <div className="w-full pt-[4px]"><Heading light={light}>Colors</Heading></div>
          <div role="group" aria-label="Color palettes" style={{ "--palette-width": light ? "340px" : "336px" } as CSSProperties} className="relative h-[56px] w-[var(--palette-width)] max-w-[calc(100%+12px)] shrink-0 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">{palettes.map(([first, second], index) => <button key={first} type="button" aria-label={`Palette ${first}`} onClick={() => { setPrimary(first.toLowerCase()); setSecondary(second.toLowerCase()); }} style={{ left: 6 + index * 54, backgroundImage: `linear-gradient(134.63598998228292deg,${first},${second})` }} className="absolute top-[8px] h-[36px] w-[46px] rounded-full border border-[var(--custom-border)]" />)}</div>
          <div className="flex w-full items-center gap-[10px] pt-[2px]"><span className="flex-1 text-[13px] leading-[19px] text-[var(--custom-muted)]">Custom colors</span><input aria-label="Primary color" type="color" value={primary} onChange={event => setPrimary(event.target.value)} className="h-[27px] w-[50px] shrink-0" /><input aria-label="Secondary color" type="color" value={secondary} onChange={event => setSecondary(event.target.value)} className="h-[27px] w-[50px] shrink-0" /></div>
          <div className="flex w-full items-center justify-between pt-[4px]"><span className="text-[13px] leading-[19px] text-[var(--custom-muted)]">Holo shine</span><button type="button" role="switch" aria-label="Holo shine" aria-checked={holo} onClick={() => setHolo(value => !value)} className={`h-[26px] w-[46px] rounded-[26px] border border-[var(--custom-border)] ${holo ? "bg-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" : "bg-[#17171b]"}`} /></div>
        </SurfaceCard>
        <PrimaryButton onClick={saveDraft} className={`!h-[50px] shrink-0 !pt-[16px] ${light ? "!shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_6px_18px_rgba(255,106,0,0.35)]" : ""}`}>Use as my player card</PrimaryButton>
        {saved && <p role="status" className="w-full font-mono text-[11px] leading-[15px] text-[var(--custom-muted)]">Player card draft saved</p>}
      </div>
    </div>
    <DashboardNavigation active="profile" light={light} className={light ? "!bottom-[-2px]" : "!left-[-1.32px] !right-[-0.68px] !bottom-[-1.83px]"} />
  </ScreenShell>;
}
