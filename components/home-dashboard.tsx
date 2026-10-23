import Link from "next/link";
import { Brand } from "./brand";
import { ScreenShell } from "./screen-shell";
import { DashboardNavigation } from "./dashboard-navigation";
import { DashboardProgressCard } from "./dashboard-progress-card";
import { DashboardChallenges } from "./dashboard-challenges";

export function HomeDashboard({ light = false }: { light?: boolean }) {
  return (
    <ScreenShell light={light} label="Home dashboard" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
      <div data-dashboard-scroll className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="relative min-h-[1100px] w-full">
          <header className="absolute inset-x-[16px] top-[18px] flex h-[42px] items-center justify-between">
            <Brand light={light} />
            <button type="button" aria-label="Notifications, 2 unread" className={`relative flex size-[42px] items-center justify-center rounded-[14px] border ${light ? "border-[#e7e8ec] bg-white shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-white/[0.09] bg-[#0d0d0f] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={light ? "/figma/dashboard-light-bell.svg" : "/figma/notification-bell.svg"} alt="" width={22} height={22} />
              <span className="absolute top-[-6px] right-[-6px] flex h-[21px] w-[24px] items-center justify-center rounded-[20px] border border-blaze/[0.35] bg-blaze font-mono text-[10px] leading-[13px] font-semibold text-white">2</span>
            </button>
          </header>
          <p className="absolute inset-x-[16px] top-[78px] font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">Welcome back</p>
          <h1 className={`absolute inset-x-[16px] top-[93px] font-display text-[28px] leading-[30.8px] font-extrabold tracking-[-0.28px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Jordan</h1>
          <p className={`absolute inset-x-[16px] top-[123.8px] text-[13px] leading-[18.85px] ${light ? "text-[#5b6270]" : "text-muted"}`}>Keep pushing.</p>
          <section aria-label="The Locker Room" className={`absolute inset-x-[16px] top-[156.64px] h-[292px] overflow-hidden rounded-[26px] border bg-white/[0.002] px-[20px] py-[22px] ${light ? "border-[#e7e8ec] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-white/[0.09] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={light ? "/figma/dashboard-light-hero.svg" : "/figma/dashboard-hero.svg"} alt="" width={light ? 358 : 354} height={292} className="absolute -top-px -left-px max-w-none" />
            <div className={`pointer-events-none absolute inset-0 bg-linear-to-b ${light ? "from-white/5 to-[#f4f3f0]/80" : "from-black/10 to-black/70"}`} />
            <p className="relative font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">The Locker Room</p>
            <h2 className={`relative mt-[12px] h-[102px] pb-[4px] font-display text-[25px] leading-[32.5px] font-semibold tracking-[4px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>ANALYZE<br />IMPROVE<br />COMPETE</h2>
            <div className="relative mt-[12px] h-[4px] w-[32px] rounded-[2px] bg-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" />
          </section>
          <div className={`absolute inset-x-[28px] top-[392.64px] flex h-[82px] items-center gap-[14px] rounded-[22px] border p-[14px] backdrop-blur-[7px] ${light ? "border-[#e7e8ec] bg-white/[0.84] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-blaze/[0.38] bg-[#0d0d0f]/[0.84] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
            <Link href={light ? "/camera/live/light" : "/camera/live"} aria-label="Start session" data-figma-destination="3345:4818" className={`relative flex size-[52px] shrink-0 items-center justify-center rounded-[26px] bg-[radial-gradient(circle_50.44px_at_18.2px_14.56px,#ff974d,#ff6a00)] ${light ? "shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "shadow-[0_0_18px_rgba(255,106,0,0.5)]"}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={light ? "/figma/dashboard-light-arrow.svg" : "/figma/session-arrow.svg"} alt="" width={24} height={24} />
            </Link>
            <div className="min-w-0 flex-1"><p className={`text-[13px] leading-[16px] font-bold tracking-[1.82px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>START SESSION</p><p className={`mt-[2.095px] text-[12px] leading-[16.2px] ${light ? "text-[#5b6270]" : "text-muted"}`}>Track your performance with AI powered<br className="max-[389px]:hidden" /> analytics.</p></div>
          </div>
          <div className="absolute inset-x-[16px] top-[567.64px]"><DashboardProgressCard light={light} /></div>
          <h2 className={`absolute inset-x-[18px] top-[820.64px] flex h-[18px] items-center gap-[8px] font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}><span className="h-[15px] w-[3px] rounded-[2px] bg-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" />Challenges</h2>
          <div className="absolute inset-x-[16px] top-[849.64px]"><DashboardChallenges light={light} /></div>
        </div>
      </div>
      <DashboardNavigation light={light} className={light ? "!bottom-[-2px]" : ""} />
    </ScreenShell>
  );
}
