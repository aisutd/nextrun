import { SurfaceCard } from "./surface-card";

export function DashboardProgressCard({ light = false }: { light?: boolean }) {
  return (
    <SurfaceCard light={light} shadow={false} gradientAngle={159.94552391081464} aria-labelledby="dashboard-progress-title" className={`flex h-[233px] flex-col gap-[12px] p-[14px] ${light ? "" : "shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
      <header className="relative flex h-[18px] shrink-0 items-center justify-between">
        <h2 id="dashboard-progress-title" className={`font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Your progress</h2>
        <span className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>Apr 26 · Pickup</span>
      </header>
      <div className="relative flex h-[142px] shrink-0 items-center gap-[18px]">
        <div className="relative size-[112px] shrink-0" role="img" aria-label="72 percent shooting efficiency">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={light ? "/figma/dashboard-light-ring.svg" : "/figma/shooting-ring.svg"} alt="" width={112} height={112} className="block max-w-none" />
          <span className={`absolute top-[39px] left-[26.06px] font-display text-[28px] leading-[34px] font-extrabold italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>72%</span>
        </div>
        <div className="min-w-0 flex-1">
          <p className={`h-[15px] font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>LATEST GAME</p>
          <dl>
            {[['PTS', '18'], ['AST', '6'], ['REB', '4']].map(([label, value], index) => <div key={label} className={`flex items-baseline justify-between ${index === 0 ? "h-[44px] pt-[9px] pb-[7px]" : index === 1 ? "h-[42px] py-[7px]" : "h-[41px] py-[7px]"} ${index < 2 ? light ? "border-b border-[#e7e8ec]" : "border-b border-white/[0.09]" : ""}`}><dt className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{label}</dt><dd className={`font-display text-[22px] leading-[27px] font-extrabold italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>{value}</dd></div>)}
          </dl>
        </div>
      </div>
      <footer className="relative flex h-[19px] shrink-0 items-center justify-between text-blaze">
        <span className="font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] uppercase">Shooting efficiency</span>
        <span className="shrink-0 pb-[3px] text-[13px] leading-[16px] font-semibold">▲ +4.2% vs last week</span>
      </footer>
    </SurfaceCard>
  );
}
