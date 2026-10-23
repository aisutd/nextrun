export function ClubHeader({ artwork = "/figma/club-header-art.svg", light = false }: { artwork?: string; light?: boolean }) {
  return (<header className={`absolute inset-x-[16px] top-[18px] h-[143px] overflow-hidden rounded-[24px] border bg-white/[0.002] px-[18px] py-[20px] ${light ? "border-blaze/45 shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-blaze/[0.38] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={artwork} alt="" width={light ? 358 : 354} height={143} className="absolute -top-px -left-px max-w-none" />
          <div className={`absolute inset-0 bg-linear-to-b ${light ? "from-white/5 to-[#f4f3f0]/80" : "from-black/10 to-black/70"}`} />
          <div className="relative flex h-[101px] items-center justify-between">
            <div className="flex flex-col gap-[4px] whitespace-nowrap"><p className="font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">Club hub</p><h1 className={`font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Westwood Ballers</h1><p className={`text-[13px] leading-[18.85px] ${light ? "text-[#5b6270]" : "text-muted"}`}>12 members · Dallas, TX</p></div>
            <div className="flex w-[84px] shrink-0 flex-col gap-[2px]"><div className="relative size-[84px]" role="img" aria-label="72 percent win rate">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={light ? "/figma/setup-light-ring.svg" : "/figma/club-win-ring.svg"} alt="" width={84} height={84} className="block max-w-none" /><span className={`absolute top-[25px] left-[12.06px] font-display text-[28px] leading-[34px] font-extrabold italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>72%</span>
            </div><p className={`text-center font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>WIN RATE</p></div>
          </div>
        </header>);
}
