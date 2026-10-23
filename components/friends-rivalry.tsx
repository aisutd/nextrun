"use client";

import { useState } from "react";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { ProgressBar } from "./progress-bar";
import { DashboardNavigation } from "./dashboard-navigation";
import { FriendsHeader, FriendsSearch, FriendsTabs } from "./friends-shared";

function RivalryCard({ light = false }: { light?: boolean }) {
  return <SurfaceCard light={light} aria-label="Head to head with Hooper23" gradientAngle={159.88661701144912} className="flex flex-col gap-[10px] p-[14px]">
    <h2 className="relative w-full text-center font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">Head to head</h2>
    <div className="relative flex h-[85px] w-full items-center justify-between py-[4px]">
      <div className="flex w-[54px] shrink-0 flex-col items-center gap-[6px]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={light ? "/figma/rivalry-light-you.svg" : "/figma/rivalry-you.svg"} alt="" width={54} height={54} className="size-[54px]" />
        <p className={`text-[14px] leading-[17px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>You</p>
      </div>
      <p aria-label="You 7, Hooper23 4" className={`font-display text-[42px] leading-[51px] font-extrabold tracking-[-0.84px] whitespace-nowrap italic ${light ? "text-[#0a0a0a]" : "text-white"}`}><span className="text-blaze">7</span> – 4</p>
      <div className="flex w-[67px] shrink-0 flex-col items-center gap-[6px]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={light ? "/figma/rivalry-light-hooper.svg" : "/figma/rivalry-hooper.svg"} alt="" width={54} height={54} className="size-[54px]" />
        <p className={`text-[14px] leading-[17px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>Hooper23</p>
      </div>
    </div>
    <ProgressBar light={light} value={64} label="Head to head share" />
    <p className={`relative w-full text-center text-[13px] leading-[19px] ${light ? "text-[#5b6270]" : "text-muted"}`}>You lead by 3. Next matchup: Saturday.</p>
  </SurfaceCard>;
}

export function FriendsRivalry({ light = false }: { light?: boolean }) {
  const [query, setQuery] = useState("");
  const matches = "Hooper23".toLowerCase().includes(query.trim().toLowerCase());
  return <ScreenShell light={light} label={light ? "Light Friends rivalry" : "Friends rivalry"} backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-full px-[16px] pt-[244px] pb-[100px]">
        <FriendsHeader light={light} />
        <FriendsSearch light={light} query={query} onQueryChange={setQuery} />
        <FriendsTabs light={light} active="Rivalry" />
        {matches ? <RivalryCard light={light} /> : <p role="status" className="py-[14px] font-mono text-[11px] leading-[15px] text-muted">No rivalries found</p>}
      </div>
    </div>
    <DashboardNavigation active="friends" light={light} className={light ? "!bottom-[-2px]" : "!left-[0.68px] !right-[-0.68px] !bottom-[0.17px]"} />
  </ScreenShell>;
}
