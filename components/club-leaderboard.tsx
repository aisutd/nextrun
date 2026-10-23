import { ClubHeader } from "./club-header";
import { ClubTabs } from "./club-tabs";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { DashboardNavigation } from "./dashboard-navigation";
import { ClubFeed } from "./club-feed";

const players = [
  { name: "PlayerOne", score: 248 }, { name: "Hooper23", score: 231 },
  { name: "BallsLife", score: 219 }, { name: "CourtVision", score: 201 },
  { name: "BucketsOnly", score: 190 },
];
const stats = [
  { label: "POINTS", value: "84.3", change: "+6.2%" },
  { label: "REBOUNDS", value: "36.7", change: "+4.8%" },
  { label: "ASSISTS", value: "18.2", change: "+3.9%" },
  { label: "STEALS", value: "9.4", change: "+2.7%" },
];
export function ClubLeaderboard({ light = false }: { light?: boolean }) {
  return <ScreenShell light={light} label="Club leaderboard" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div data-club-scroll className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-[1140px] w-full">
        <ClubHeader light={light} artwork={light ? "/figma/setup-light-header.svg" : undefined} />
        <ClubTabs active="leaderboard" light={light} />
        <div className="absolute inset-x-[16px] top-[221px]"><SurfaceCard light={light} gradientAngle={160.04889924993338} aria-labelledby="club-top-five" className="h-[333px] p-[14px]">
          <h2 id="club-top-five" className={`relative h-[18px] font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Top 5 this week</h2>
          <ol className="relative">{players.map((player, index) => <li key={player.name} className={`flex h-[57px] items-center gap-[10px] border-t py-[10px] ${light ? "border-[#e7e8ec]" : "border-white/[0.09]"}`}>
            <span className={`w-[22px] shrink-0 font-display text-[16px] leading-[20px] font-extrabold italic ${index < 3 ? "text-blaze [text-shadow:0_0_10px_rgba(255,106,0,0.6)]" : light ? "text-[#5b6270]" : "text-muted"}`}>{index + 1}</span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={light ? "/figma/club-light-player-avatar.svg" : "/figma/club-player-avatar.svg"} alt="" width={36} height={36} className="block shrink-0 max-w-none" />
            <span className={`min-w-0 flex-1 text-[14px] leading-[17px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>{player.name}</span><span className={`font-mono text-[13px] leading-[17px] font-bold ${light ? "text-[#0a0a0a]" : "text-white"}`}>{player.score}</span>
          </li>)}</ol>
        </SurfaceCard></div>
        <h2 className={`absolute inset-x-[18px] top-[575px] flex h-[18px] items-center gap-[8px] font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}><span className="h-[15px] w-[3px] rounded-[2px] bg-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" />Team stats</h2>
        <div className="absolute inset-x-[16px] top-[604px] grid grid-cols-2 gap-x-[10px] gap-y-[9px]">{stats.map(stat => <SurfaceCard light={light} key={stat.label} gradientAngle={159.6846502457053} className="flex h-[106px] flex-col gap-[4px] px-[14px] pt-[17px] pb-[15px]"><p className={`relative font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{stat.label}</p><p className={`relative font-display text-[28px] leading-[34px] font-extrabold italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>{stat.value}</p><p className="relative text-[12px] leading-[15px] font-semibold text-[#22c55e]">▲ {stat.change}</p></SurfaceCard>)}</div>
        <div className={`absolute inset-x-[16px] ${light ? "top-[824px]" : "top-[832px]"}`}><ClubFeed light={light} /></div>
      </div>
    </div>
    <DashboardNavigation active="club" light={light} className={light ? "!bottom-[-2px]" : "translate-x-[-0.32px] translate-y-[-0.17px]"} />
  </ScreenShell>;
}
