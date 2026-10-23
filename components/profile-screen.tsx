import Link from "next/link";
import type { CSSProperties } from "react";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { PrimaryLink } from "./primary-button";
import { ProgressBar } from "./progress-bar";
import { DashboardNavigation } from "./dashboard-navigation";
import { PlayerCard } from "./player-card";

function ProfileSectionHeading({ children, top, light = false }: { children: string; top: number; light?: boolean }) {
  return <div style={{ top }} className="absolute inset-x-[18px] flex h-[18px] items-center gap-[8px]">
    <span aria-hidden="true" className="h-[15px] w-[3px] rounded-[2px] bg-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" />
    <h2 className="font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] text-[var(--profile-text)] italic">{children}</h2>
  </div>;
}

export function ProfileScreen({ light = false }: { light?: boolean }) {
  return <ScreenShell light={light} label={light ? "Light player profile" : "Player profile"} backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div style={{ "--profile-text": light ? "#0a0a0a" : "#fff", "--profile-muted": light ? "#5b6270" : "#9ca3af" } as CSSProperties} className={`relative h-[1480px] w-full ${light ? "" : "-left-[0.32px] -top-[0.17px]"}`}>
        <header className="absolute inset-x-[16px] top-[18px] flex h-[42px] items-center justify-between">
          <div><p className="font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">Profile</p><h1 className="font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] text-[var(--profile-text)] italic">Player card</h1></div>
          <Link href={light ? "/settings/light" : "/settings"} aria-label="Settings" className={`relative flex size-[42px] shrink-0 items-center justify-center rounded-[14px] border ${light ? "border-[#e7e8ec] bg-white shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "left-[1.17px] border-white/[0.09] bg-[#0d0d0f] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={light ? "/figma/profile-light-settings.svg" : "/figma/profile-settings.svg"} alt="" width={22} height={22} />
          </Link>
        </header>
        <div className={`absolute inset-x-[16px] top-[74px] flex h-[348px] items-center justify-center overflow-hidden rounded-[24px] border bg-white/[0.002] ${light ? "border-[#e7e8ec] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-white/[0.09] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={light ? "/figma/profile-light-court.svg" : "/figma/profile-court.svg"} alt="" width={light ? 358 : 354} height={348} className={`absolute -top-px -left-px h-[348px] max-w-none ${light ? "w-[358px]" : "w-[354px]"}`} />
          <span aria-hidden="true" className={`absolute inset-0 bg-linear-to-b ${light ? "from-white/5 to-[#f4f3f0]/80" : "from-black/10 to-black/70"}`} />
          <PlayerCard light={light} />
        </div>
        {light && <p className="absolute top-[452px] right-[14px] left-[18px] pt-[4px] text-center font-mono text-[11px] leading-[15px] text-[#5b6270]">Tap the card to flip</p>}
        <div className={light ? "absolute inset-x-[16px] top-[491px]" : "absolute right-[16.32px] left-[15.68px] top-[471.83px]"}><PrimaryLink href={light ? "/profile/custom-card/light" : "/profile/custom-card"} className={light ? "!shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_6px_18px_rgba(255,106,0,0.35)]" : ""}>Build a custom card</PrimaryLink></div>
        <ProfileSectionHeading top={560}>Attributes</ProfileSectionHeading>
        <div className="absolute inset-x-[16px] top-[589px]"><SurfaceCard light={light} aria-label="Player attributes" gradientAngle={159.90929729803355} className="flex flex-col gap-[8px] p-[14px]">
          {[["Shooting", 92], ["Playmaking", 88], ["Athleticism", 85], ["Defense", 78]].map(([label, value], index) => <div key={label} className={`relative flex flex-col gap-[8px] ${index > 0 ? "pt-[4px]" : ""}`}>
            <div className="flex h-[16px] items-center justify-between"><span className="text-[13px] leading-[16px] text-[var(--profile-text)]">{label}</span><span className="font-mono text-[11px] leading-[15px] font-bold text-[var(--profile-text)]">{value}</span></div>
            <ProgressBar light={light} value={Number(value)} label={String(label)} />
          </div>)}
        </SurfaceCard></div>
        <ProfileSectionHeading top={799}>Achievements</ProfileSectionHeading>
        <div className="absolute inset-x-[16px] top-[828px]"><SurfaceCard light={light} aria-label="Achievements" gradientAngle={159.7714520169294} className="h-[112px] overflow-x-auto p-[14px] [scrollbar-width:none]">
          <div className="relative flex gap-[21.1px] pr-[9.25px] pl-[6.27px]">
            {["Sharpshooter", "Quick hands", "Champion", "On fire"].map((label, index) => <div key={label} className="flex shrink-0 flex-col items-start gap-[6px]" style={{ paddingLeft: [0, 0, 2.98, 3.4][index] }}>
              <div className="relative h-[64px] w-[58px] bg-blaze drop-shadow-[0_0_3px_rgba(255,106,0,0.5)]"><div className={`absolute inset-[2px] flex items-center justify-center ${light ? "bg-white" : "bg-[#120a05]"}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/figma/profile-achievement-${index}.svg`} alt="" width={24} height={24} />
              </div></div>
              <p className="w-full text-center text-[10px] leading-[12px] whitespace-nowrap text-[var(--profile-muted)]">{label}</p>
            </div>)}
          </div>
        </SurfaceCard></div>
        <ProfileSectionHeading top={960}>Border glow</ProfileSectionHeading>
        <ProfileSectionHeading top={1059}>Title</ProfileSectionHeading>
        <ProfileSectionHeading top={1157}>Recent activity</ProfileSectionHeading>
        {[["Apr 26 · Pickup", "18 pts · 6 ast"], ["Apr 22 · Tournament", "24 pts · 4 ast"], ["Apr 19 · Solo drills", "82% FT"], ["Apr 15 · Pickup", "12 pts · 9 ast"]].map(([label, value], index) => <div key={label} style={{ top: 1186 + index * 50 }} className="absolute inset-x-[16px]"><SurfaceCard light={light} shadow={false} gradientAngle={159.19272818322625} className="flex h-[42px] items-center justify-between px-[14px] py-[12px]"><span className="text-[13px] leading-[16px] text-[var(--profile-text)]">{label}</span><span className="font-mono text-[11px] leading-[15px] whitespace-nowrap text-[var(--profile-muted)]">{value}</span></SurfaceCard></div>)}
      </div>
    </div>
    <DashboardNavigation active="profile" light={light} className={light ? "!bottom-[-2px]" : "!right-[-2px]"} />
  </ScreenShell>;
}
