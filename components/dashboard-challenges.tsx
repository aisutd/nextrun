import { SurfaceCard } from "./surface-card";
import { ProgressBar } from "./progress-bar";

export function DashboardChallenges({ light = false }: { light?: boolean }) {
  return (
    <SurfaceCard light={light} shadow={false} gradientAngle={159.85838539273809} className="flex h-[151px] flex-col gap-[8px] p-[14px]">
      {[{label:"Make 10 3PTs this week",value:60},{label:"Log 3 sessions",value:33},{label:"5 assists in one game",value:100}].map((challenge,index)=><div key={challenge.label} className="contents">
        <div className={`relative flex shrink-0 items-center justify-between ${index ? "h-[22px] pt-[6px]" : "h-[16px]"}`}><span className={`text-[13px] leading-[16px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>{challenge.label}</span><span className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{challenge.value}%</span></div>
        {index===2 ? <ProgressBar light={light} value={100} label={challenge.label} /> : <div role="progressbar" aria-label={challenge.label} aria-valuenow={challenge.value} aria-valuemin={0} aria-valuemax={100} className={`relative h-[7px] w-full shrink-0 rounded-[8px] ${light ? "bg-[#f2f3f5]" : "bg-[#17171b]"}`} />}
      </div>)}
    </SurfaceCard>
  );
}
