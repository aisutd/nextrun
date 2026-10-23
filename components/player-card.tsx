"use client";

import { useState } from "react";

/** Both measured Figma component variants, toggled by its original tap reaction. */
export function PlayerCard({ initialAlternate = false, light = false }: { initialAlternate?: boolean; light?: boolean }) {
  const [alternate, setAlternate] = useState(initialAlternate);
  return <button type="button" aria-label="Change player card variant" aria-pressed={alternate} onClick={() => setAlternate(value => !value)} className="relative h-[310px] w-[224px] shrink-0 text-left text-white">
    {alternate ? <div className="absolute inset-0 overflow-hidden rounded-[16px] bg-[linear-gradient(210deg,#ff6a00_0%,#0a0a0a_85%)] shadow-[inset_0_0_30px_rgba(0,0,0,0.6)]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/figma/profile-card-back-art.svg" alt="" width={224} height={310} className="absolute inset-0 -scale-x-100" />
      {light && <span aria-hidden="true" className="pointer-events-none absolute inset-0 bg-[linear-gradient(79.4344deg,transparent_35%,rgba(255,255,255,0.14)_50%,transparent_65%)]" />}
      <div className="absolute inset-x-[22px] top-[78px] grid grid-cols-2 gap-[8px]">{Array.from({ length: 6 }, (_, index) => <span key={index} className={`h-[64px] rounded-[14px] border bg-black/35 ${light ? "border-[#e7e8ec]" : "border-white/[0.09]"}`} />)}</div>
      {light && <span aria-hidden="true" className="pointer-events-none absolute inset-[8px] rounded-[9px] border-2 border-white/85 bg-white/[0.002] shadow-[inset_0_0_14px_2px_rgba(255,255,255,0.35)]" />}
    </div> : <div className="absolute inset-0 overflow-hidden rounded-[22px] border-[3px] border-blaze bg-[radial-gradient(ellipse_245.67px_243.81px_at_50%_30%,rgba(255,106,0,0.333)_0%,#0a0a0a_70%)] p-[14px] shadow-[0_0_28px_#ff6a00]">
      <div className="relative flex h-[64px] w-full items-start justify-between">
        <div className="pt-[3px]"><p className="font-mono text-[11px] leading-[15px] tracking-[2.2px] opacity-80">OVR</p><p className="font-display text-[46px] leading-[46px] font-extrabold italic">92</p></div>
        <span className="rounded-[6px] border border-white/55 px-[8px] py-[3px] font-mono text-[11px] leading-[15px]">PG</span>
      </div>
      <div className="relative flex h-[128px] items-start justify-center py-[8px]">
        {/* The 10px export inset contains the original drop shadow. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/figma/profile-player.svg" alt="" width={116} height={132} className="absolute top-[-2px] h-[132px] w-[116px] max-w-none" />
      </div>
      <p className="relative font-display text-[20px] leading-[24px] font-extrabold italic">@playerone</p>
      <p className="relative font-mono text-[11px] leading-[15px] text-blaze">Rookie · #24</p>
      <span aria-hidden="true" className="pointer-events-none absolute inset-[9px] rounded-[15px] border border-blaze/50" />
      <span aria-hidden="true" className="pointer-events-none absolute inset-0 rounded-[inherit] shadow-[inset_0_0_30px_3px_rgba(0,0,0,0.6)]" />
    </div>}
  </button>;
}
