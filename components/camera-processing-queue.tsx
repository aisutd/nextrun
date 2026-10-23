import { SurfaceCard } from "./surface-card";
import { ProgressBar } from "./progress-bar";

const queue = [
  { name: "Sat_run_full.mp4", progress: 64 },
  { name: "Drills_Tue.mp4", progress: 18 },
];

/** Supplied Figma queue state; live processing can supply these values later. */
export function CameraProcessingQueue({ light = false }: { light?: boolean }) {
  return <SurfaceCard light={light} gradientAngle={159.54626008924924} aria-labelledby="processing-queue" className="flex h-[135px] flex-col gap-[8px] p-[14px]">
    <header className="relative flex h-[21px] shrink-0 items-center justify-between">
      <h2 id="processing-queue" className={`font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Processing queue</h2>
      <span className="rounded-[20px] border border-blaze/[0.35] bg-blaze/15 px-[8px] py-[3px] font-mono text-[10px] leading-[13px] font-semibold text-blaze">2 IN QUEUE</span>
    </header>
    {queue.map(item => <div key={item.name} className="relative flex flex-col gap-[8px]">
      <p className={`h-[19px] pt-[4px] font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{item.name} — {item.progress}%</p>
      <ProgressBar light={light} value={item.progress} label={`Processing ${item.name}`} />
    </div>)}
  </SurfaceCard>;
}
