import { ScreenShell } from "./screen-shell";
import { ClubHeader } from "./club-header";
import { ClubTabs } from "./club-tabs";
import { ClubFeed } from "./club-feed";
import { SurfaceCard } from "./surface-card";
import { DashboardNavigation } from "./dashboard-navigation";

const activities = [
  { title: "Game vs. Rivals", detail: "W 78 – 62", date: "Apr 26", icon: "game" },
  { title: "Practice Session", detail: "+3 new records", date: "Apr 24", icon: "practice" },
];

export function ClubActivity({ light = false }: { light?: boolean }) {
  return <ScreenShell light={light} label="Club activity" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-full w-full pb-[90px]">
        <ClubHeader light={light} artwork={light ? "/figma/setup-light-header.svg" : "/figma/activity-header-art.svg"} />
        <ClubTabs active="activity" light={light} />
        <div className="px-[16px] pt-[221px]">
          <SurfaceCard light={light} gradientAngle={159.993063510619} aria-labelledby="recent-activity" className="h-[166px] p-[14px]">
            <h2 id="recent-activity" className={`relative h-[18px] font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Recent activity</h2>
            <ul className="relative">{activities.map(activity => <li key={activity.icon} className={`flex h-[59px] items-center gap-[10px] border-t py-[10px] ${light ? "border-[#e7e8ec]" : "border-white/[0.09]"}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`/figma/activity-${light ? "light-" : ""}${activity.icon}.svg`} alt="" width={38} height={38} className="block shrink-0 max-w-none" />
              <div className="min-w-0 flex-1"><p className={`text-[14px] leading-[17px] font-bold ${light ? "text-[#0a0a0a]" : "text-white"}`}>{activity.title}</p><p className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{activity.detail}</p></div>
              <span className={`shrink-0 font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{activity.date}</span>
            </li>)}</ul>
          </SurfaceCard>
          <div className="mt-[13px]"><ClubFeed avatars light={light} /></div>
        </div>
      </div>
    </div>
    <DashboardNavigation active="club" light={light} className={light ? "!bottom-[-2px]" : "translate-x-[-0.32px] translate-y-[-1.17px]"} />
  </ScreenShell>;
}
