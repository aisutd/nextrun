import { ScreenShell } from "./screen-shell";
import { ClubHeader } from "./club-header";
import { ClubTabs } from "./club-tabs";
import { SurfaceCard } from "./surface-card";
import { DashboardNavigation } from "./dashboard-navigation";

const rounds = ["Quarterfinals — Sat 4 PM", "Semifinals — Sun 2 PM", "Finals — Sun 6 PM"];

export function ClubTournaments({ light = false }: { light?: boolean }) {
  return <ScreenShell light={light} label="Club tournaments" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-full w-full pb-[90px]">
        <ClubHeader light={light} artwork={light ? "/figma/setup-light-header.svg" : "/figma/tournament-header-art.svg"} />
        <ClubTabs active="tournaments" light={light} />
        <div className="px-[16px] pt-[221px]">
          <SurfaceCard light={light} gradientAngle={160.01162496734605} aria-labelledby="summer-showdown" className="flex h-[231px] flex-col gap-[6px] p-[14px]">
            <h2 id="summer-showdown" className={`relative h-[18px] shrink-0 font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Summer Showdown</h2>
            <p className={`relative h-[19px] shrink-0 text-[13px] leading-[18.85px] ${light ? "text-[#5b6270]" : "text-muted"}`}>8 teams · single elimination</p>
            <ol className="relative flex flex-col gap-[6px]">{rounds.map((round, index) => <li key={round} className={`flex shrink-0 items-center gap-[10px] rounded-[14px] border px-[12px] pb-[12px] ${light ? "border-[#e7e8ec] bg-[#f2f3f5]" : "border-white/[0.09] bg-[#17171b]"} ${index === 0 ? "h-[48px] pt-[16px]" : "h-[46px] pt-[14px]"}`}>
              <span aria-hidden="true" className={`h-[18px] w-[3px] shrink-0 rounded-[2px] bg-blaze ${light ? "shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "shadow-[0_0_18px_rgba(255,106,0,0.5)]"}`} />
              <span className={`text-[13px] leading-[16px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>{round}</span>
            </li>)}</ol>
          </SurfaceCard>
        </div>
      </div>
    </div>
    <DashboardNavigation active="club" light={light} className={light ? "!bottom-[-2px]" : "translate-x-[-0.32px] translate-y-[-1.17px]"} />
  </ScreenShell>;
}
