"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { DashboardNavigation } from "./dashboard-navigation";

const accents = [
  { name: "Orange", color: "#ff6a00", left: 6, width: 87 },
  { name: "Cyan", color: "#00e5ff", left: 97, width: 74 },
  { name: "Lime", color: "#b6ff00", left: 175.34, width: 72 },
  { name: "Magenta", color: "#ff2bd6", left: 251.45, width: 96 },
  { name: "Violet", color: "#9b5cff", left: 350.83, width: 78 },
  { name: "Electric Blue", color: "#2e7bff", left: 432.77, width: 117 },
  { name: "Hot Pink", color: "#ff3d81", left: 553.27, width: 93 },
] as const;

function SettingsHeading({ children, light = false }: { children: ReactNode; light?: boolean }) {
  return <h2 className={`relative w-full font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] ${light ? "text-[#0a0a0a]" : "text-white"} italic`}>{children}</h2>;
}

export function SettingsScreen({ light = false }: { light?: boolean }) {
  const router = useRouter();
  const scrollPane = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const savedScroll = sessionStorage.getItem("nextrun.settingsThemeScroll");
    if (savedScroll !== null && scrollPane.current) { scrollPane.current.scrollTop = Number(savedScroll); sessionStorage.removeItem("nextrun.settingsThemeScroll"); }
  }, [light]);
  function toggleTheme() {
    sessionStorage.setItem("nextrun.settingsThemeScroll", String(scrollPane.current?.scrollTop ?? 0));
    router.push(light ? "/settings" : "/settings/light", { scroll: false });
  }
  const [accent, setAccent] = useState("Orange");
  const [privacy, setPrivacy] = useState(light ? "Club" : "Public");
  const [feedback, setFeedback] = useState("");
  function selectAccent(name: string) {
    setAccent(name);
    sessionStorage.setItem("nextrun.accentDraft", name);
  }
  function selectPrivacy(value: string) {
    setPrivacy(value);
    sessionStorage.setItem("nextrun.privacyDraft", value);
  }
  return <ScreenShell light={light} label={light ? "Light Settings" : "Settings"} backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div ref={scrollPane} style={{ "--settings-text": light ? "#0a0a0a" : "#fff", "--settings-muted": light ? "#5b6270" : "#9ca3af" } as React.CSSProperties} className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className={`relative flex w-full flex-col items-center gap-[10px] px-[16px] pb-[110px] ${light ? "pt-[45px]" : "-left-[0.32px] pt-[35.83px]"}`}>
        <header className="flex h-[42px] w-full shrink-0 items-center gap-[10px]">
          <Link href={light ? "/profile/light" : "/profile"} aria-label="Back to Profile" className={`flex size-[42px] shrink-0 items-center justify-center rounded-[14px] border text-[15px] leading-[18px] font-semibold ${light ? "border-[#e7e8ec] bg-white text-[#0a0a0a] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-white/[0.09] bg-[#0d0d0f] text-white shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>‹</Link>
          <h1 className="font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] text-[var(--settings-text)] italic">Settings</h1>
        </header>
        <section aria-label="NextRun Lab" className="relative flex h-[156px] w-full shrink-0 flex-col justify-end overflow-hidden rounded-[24px] border border-blaze/[0.38] px-[18px] pt-[22px] pb-[18px] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]" style={{ borderColor: light ? "rgba(255,106,0,0.45)" : undefined, boxShadow: light ? "0 10px 28px rgba(18,20,30,0.07),0 1px 2px rgba(18,20,30,0.06)" : undefined, backgroundImage: light ? "radial-gradient(ellipse 429.6px 156px at 78% 10%,rgba(255,106,0,0.38) 0%,rgba(255,106,0,0) 62%),linear-gradient(180deg,#fff,#fff3e8)" : "radial-gradient(ellipse 424.8px 156px at 78% 10%,rgba(255,106,0,0.55) 0%,rgba(255,106,0,0) 60%),linear-gradient(180deg,#15100b,#050505)" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={light ? "/figma/settings-light-grid.svg" : "/figma/settings-grid.svg"} alt="" width={light ? 356 : 352} height={150} className={`absolute top-[4px] left-0 h-[150px] max-w-none ${light ? "w-[356px]" : "w-[352px]"}`} />
          {/* Ancestor clipping is included in this original Figma asset export. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={light ? "/figma/settings-light-ball.svg" : "/figma/settings-ball.svg"} alt="" width={165} height={143} className="absolute -top-px h-[143px] w-[165px] max-w-none" style={{ left: light ? 192 : 188 }} />
          <p className="relative font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">NextRun</p>
          <h2 className="relative pt-[2px] font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] text-[var(--settings-text)] italic">NextRun Lab</h2>
          <p className="relative text-[13px] leading-[19px] text-[var(--settings-text)] opacity-80">Turn on your potential.</p>
        </section>
        <SurfaceCard light={light} aria-label="App theme" gradientAngle={158.2619052164566} shadowTop={1} className="flex h-[65px] shrink-0 items-center justify-between px-[14px] pt-[16px] pb-[14px]">
          <div className="relative"><h2 className="text-[14px] leading-[17px] font-bold text-[var(--settings-text)]">Light mode</h2><p className="font-mono text-[11px] leading-[15px] text-[var(--settings-muted)]">Switch app theme</p></div>
          <button type="button" role="switch" aria-checked={light} aria-label="Light mode" onClick={toggleTheme} className={`relative h-[26px] w-[46px] shrink-0 rounded-[26px] border p-[2px] ${light ? "border-[#e7e8ec] bg-blaze shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "border-white/[0.09] bg-[#17171b]"}`}><span className={`block size-[20px] rounded-[10px] ${light ? "ml-[20px] bg-white" : "bg-muted"}`} /></button>
        </SurfaceCard>
        <SurfaceCard light={light} aria-label="Accent color" gradientAngle={165.04108097849735} shadowTop={1} className={`flex max-[389px]:h-auto shrink-0 flex-col items-center gap-[2px] px-[14px] pt-[16px] pb-[14px] ${light ? "h-[163.42px]" : "h-[147.42px]"}`}>
          <SettingsHeading light={light}>Accent color</SettingsHeading>
          <p className="relative w-full pt-[1.42px] text-[13px] leading-[19px] text-[var(--settings-muted)]">Pick a neon color for buttons, glows and highlights.<br />Orange is the default.</p>
          <div role="group" aria-label="Accent colors" className={`relative max-w-[calc(100%+12px)] shrink-0 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${light ? "h-[70px] w-[340px]" : "h-[54px] w-[336px]"}`}>{accents.map(item => <button key={item.name} type="button" aria-label={item.name} aria-pressed={accent === item.name} onClick={() => selectAccent(item.name)} style={{ left: item.left, width: item.width }} className={`absolute top-[8px] flex h-[38px] items-center justify-center rounded-full border text-[12px] leading-[15px] font-semibold whitespace-nowrap ${light ? "text-[#0a0a0a]" : "text-white"} ${accent === item.name ? "border-blaze bg-blaze/10 shadow-[0_0_18px_rgba(255,106,0,0.5)]" : light ? "border-[#e7e8ec] bg-white" : "border-white/[0.09] bg-[#0d0d0f]"}`}><span style={{ color: item.color }}>●</span>&nbsp;{item.name}</button>)}</div>
        </SurfaceCard>
        <SurfaceCard light={light} aria-label="Privacy" gradientAngle={159.65570334145724} shadowTop={1} className="flex h-[132px] shrink-0 flex-col items-center gap-[4px] px-[14px] pt-[16px] pb-[14px]">
          <SettingsHeading light={light}>Privacy</SettingsHeading>
          <p className="relative w-full text-[13px] leading-[19px] text-[var(--settings-muted)]">Who can see your profile and stats.</p>
          <div role="group" aria-label="Profile visibility" style={{ "--rail-width": light ? "340px" : "336px" } as React.CSSProperties} className="relative flex h-[55px] w-[var(--rail-width)] max-w-[calc(100%+12px)] shrink-0 gap-[8px] overflow-x-auto rounded-[12px] px-[6px] pt-[6px] pb-[12px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">{["Public", "Club", "Private"].map((value, index) => <button key={value} type="button" aria-pressed={privacy === value} onClick={() => selectPrivacy(value)} style={{ width: (light ? [105.36,96.34,110.3] : [104.03,95.02,108.95])[index] }} className={`flex h-[37px] shrink-0 items-center justify-center rounded-full border text-[12px] leading-[15px] font-semibold ${privacy === value ? "border-blaze bg-linear-to-b from-[#ff7f24] to-blaze text-white shadow-[0_0_18px_rgba(255,106,0,0.5)]" : light ? "border-[#e7e8ec] bg-white text-[#5b6270]" : "border-white/[0.09] bg-[#0d0d0f] text-[var(--settings-muted)]"}`}>{value}</button>)}</div>
        </SurfaceCard>
        <SurfaceCard light={light} aria-label="Processing queue" gradientAngle={158.62174721660074} shadowTop={1} className="flex h-[53px] shrink-0 items-center justify-between px-[14px] pt-[16px] pb-[14px]">
          <SettingsHeading light={light}>Processing queue</SettingsHeading><span className="relative shrink-0 rounded-[20px] border border-blaze/35 bg-blaze/15 px-[8px] py-[3px] font-mono text-[10px] leading-[13px] font-semibold text-blaze">2 UPLOADING</span>
        </SurfaceCard>
        <SurfaceCard light={light} aria-label="Legal" gradientAngle={159.5272469783479} shadowTop={1} className="flex h-[98px] shrink-0 flex-col gap-[6px] px-[14px] pt-[16px] pb-[14px]">
          <SettingsHeading light={light}>Legal</SettingsHeading>
          <p className="relative pt-[2px] text-[14px] leading-[17px] text-blaze">Terms of Service</p><p className="relative text-[14px] leading-[17px] text-blaze">Privacy Policy</p>
        </SurfaceCard>
        <button type="button" onClick={() => setFeedback("Account deletion is not connected to an account service.")} className={`relative flex h-[50px] w-full shrink-0 items-center justify-center rounded-[16px] border border-[#ef4444] bg-[#0d0d0f] px-[14px] pt-[16px] pb-[14px] text-[15px] leading-[18px] font-semibold text-[#ef4444] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)] ${light ? "!bg-white !shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : ""}`}>Delete account</button>
        <p className="w-full text-center font-mono text-[11px] leading-[15px] text-[var(--settings-muted)]">NextRun · Version 1.0.0</p>
        {feedback && <p role="status" className="w-full font-mono text-[11px] leading-[15px] text-[var(--settings-muted)]">{feedback}</p>}
      </div>
    </div>
    <DashboardNavigation active="profile" light={light} className={light ? "!bottom-[-2px]" : "!left-[-0.32px] !right-[-1.68px] !bottom-[0.17px]"} />
  </ScreenShell>;
}
