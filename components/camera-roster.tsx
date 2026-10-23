"use client";
import { useState } from "react";
import { SurfaceCard } from "./surface-card";

type Team = "–" | "A" | "B";
const players = ["PlayerOne", "Hooper23", "BallsLife", "CourtVision", "BucketsOnly"];

export function CameraRoster({ light = false }: { light?: boolean }) {
  const [teams, setTeams] = useState<Team[]>(["A", "B", "–", "–", "–"]);
  return <SurfaceCard light={light} gradientAngle={160.79031264038693} aria-labelledby="camera-roster" className={`${light ? "h-[318px]" : "h-[310px]"} p-[14px]`}>
    <header className="relative flex h-[18px] items-center justify-between"><h2 id="camera-roster" className={`font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Roster</h2><p aria-live="polite" className={`font-mono text-[11px] leading-[15px] whitespace-pre ${light ? "text-[#5b6270]" : "text-muted"}`}>{`Team A · ${teams.filter(t => t === "A").length}  |  Team B · ${teams.filter(t => t === "B").length}`}</p></header>
    <ul className="relative">{players.map((player, index) => <li key={player} className={`flex h-[54px] items-center justify-between gap-[10px] border-t py-[9px] ${light ? "border-[#e7e8ec]" : "border-white/[0.09]"}`}>
      <div className="flex min-w-0 items-center gap-[10px]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={light ? "/figma/camera-light-avatar.svg" : "/figma/camera-player-avatar.svg"} alt="" width={34} height={34} className="block shrink-0 max-w-none" /><span className={`truncate text-[14px] leading-[17px] ${light ? "text-[#0a0a0a]" : "text-white"}`}>{player}</span>
      </div>
      <div role="group" aria-label={`Team for ${player}`} className={`flex h-[35px] w-[118.21px] shrink-0 items-start gap-[3px] rounded-full border p-[3px] ${light ? "border-[#e7e8ec] bg-[#f2f3f5]" : "border-white/[0.09] bg-[#17171b]"}`}>{(["–", "A", "B"] as const).map((team, teamIndex) => <button key={team} type="button" aria-label={team === "–" ? "Unassigned" : `Team ${team}`} aria-pressed={teams[index] === team} onClick={() => setTeams(teams.map((current, i) => i === index ? team : current))} style={{ width: [34.5, 34.98, 34.73][teamIndex] }} className={`flex h-[27px] shrink-0 items-center justify-center rounded-full text-[11px] leading-[13px] font-bold ${light ? teams[index] === team ? team === "A" ? "bg-blaze text-white shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : team === "B" ? "bg-[#0a0a0a] text-white" : "bg-[#e7e8ec] text-[#0a0a0a]" : "text-[#5b6270]" : teams[index] === team ? team === "A" ? "bg-linear-to-b from-[#ff7f24] to-blaze text-white shadow-[0_0_18px_rgba(255,106,0,0.5)]" : team === "B" ? "bg-white text-[#050506]" : "bg-white/[0.09] text-white" : "text-muted"}`}>{team}</button>)}</div>
    </li>)}</ul>
  </SurfaceCard>;
}
