"use client";

import { FriendsHeader, FriendsSearch, FriendsTabs } from "./friends-shared";
import { useState } from "react";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { DashboardNavigation } from "./dashboard-navigation";

const friends = [
  { name: "PlayerOne", status: "In a game · 2h", color: "#22c55e", online: true },
  { name: "Hooper23", status: "At practice · 34m", color: "#ff6a00", online: true },
  { name: "BallsLife", status: "Offline · 3h", color: "#9ca3af", online: false },
  { name: "CourtVision", status: "In club · 1h", color: "#22c55e", online: true },
  { name: "BucketsOnly", status: "Offline · 5h", color: "#9ca3af", online: false },
  { name: "DunkMaster", status: "Busy · 45m", color: "#ef4444", online: true },
] as const;

function FriendPresenceCard({ friend, light = false }: { friend: (typeof friends)[number]; light?: boolean }) {
  return <SurfaceCard light={light} aria-label={friend.name} gradientAngle={159.5666989013967} className="flex h-[70px] items-center gap-[12px] px-[14px] py-[11px]">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={light ? "/figma/friends-light-avatar.svg" : "/figma/friends-avatar.svg"} alt="" width={46} height={46} className="relative size-[46px] shrink-0" />
    <div className="relative min-w-0 flex-1">
      <h2 className={`text-[14px] leading-[17px] font-bold ${light ? "text-[#0a0a0a]" : "text-white"}`}>{friend.name}</h2>
      <p className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{friend.status}</p>
    </div>
    <span aria-hidden="true" className="relative size-[9px] shrink-0 rounded-full" style={{ backgroundColor: light && !friend.online ? "#5b6270" : friend.color, boxShadow: friend.online ? `0 0 8px ${friend.color}` : undefined }} />
  </SurfaceCard>;
}

export function FriendsActive({ light = false }: { light?: boolean }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const visible = friends.filter(friend => friend.name.toLowerCase().includes(query.trim().toLowerCase()) && (filter === "All" || filter === "Online" && friend.online || filter === "Offline" && !friend.online));
  return <ScreenShell light={light} label="Friends active" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-full pb-[100px]">
        <FriendsHeader light={light} />
        <FriendsSearch light={light} query={query} onQueryChange={setQuery} />
        <FriendsTabs light={light} active="Active" />
        <div role="group" aria-label="Filter friends" className="absolute inset-x-[10px] top-[236px] flex gap-[8px] overflow-x-auto px-[6px] pt-[8px] pb-[12px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {["All", "Online", "Offline", "Requests"].map((label, index) => <button key={label} style={{ width: [45, 68, 70, 85][index] }} type="button" aria-pressed={filter === label} onClick={() => setFilter(label)} className={`h-[33px] shrink-0 rounded-full border px-[14px] py-[8px] text-[12px] leading-[15px] font-semibold ${light ? "text-[#0a0a0a]" : "text-white"} ${filter === label ? `border-blaze bg-blaze/10 ${light ? "shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "shadow-[0_0_18px_rgba(255,106,0,0.5)]"}` : light ? "border-[#e7e8ec] bg-white" : "border-white/[0.09] bg-[#0d0d0f]"}`}>{label}</button>)}
        </div>
        <div aria-live="polite" className="flex flex-col gap-[12px] px-[16px] pt-[299px]">
          {visible.map(friend => <FriendPresenceCard key={friend.name} friend={friend} light={light} />)}
          {visible.length === 0 && <p className={`py-[14px] font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>{filter === "Requests" ? "No pending requests" : "No friends found"}</p>}
        </div>
      </div>
    </div>
    <DashboardNavigation light={light} active="friends" className={light ? "!bottom-[-2px]" : "!left-[-0.32px] !right-[0.32px] !bottom-[0.17px]"} />
  </ScreenShell>;
}
