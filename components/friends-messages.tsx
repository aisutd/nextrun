"use client";

import { useState, type FormEvent } from "react";
import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { PrimaryButton } from "./primary-button";
import { DashboardNavigation } from "./dashboard-navigation";
import { FriendsHeader, FriendsSearch, FriendsTabs } from "./friends-shared";

export function FriendsMessages({ light = false }: { light?: boolean }) {
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<string[]>([]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;
    setMessages(current => [...current, draft.trim()]);
    setDraft("");
  }
  const matches = "Hooper23".toLowerCase().includes(query.trim().toLowerCase());
  return <ScreenShell light={light} label="Friends messages" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-full px-[16px] pt-[244px] pb-[100px]">
        <FriendsHeader light={light} />
        <FriendsSearch light={light} query={query} onQueryChange={setQuery} />
        <FriendsTabs light={light} active="Messages" />
        {matches ? <SurfaceCard light={light} aria-label="Conversation with Hooper23" gradientAngle={160.00116958190927} className="flex flex-col gap-[8px] p-[14px]">
          <header className={`relative flex h-[49px] w-full items-center gap-[10px] border-b pb-[10px] ${light ? "border-[#e7e8ec]" : "border-white/[0.09]"}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={light ? "/figma/friends-light-message-avatar.svg" : "/figma/friends-message-avatar.svg"} alt="" width={38} height={38} className="size-[38px] shrink-0" />
            <div>
              <h2 className={`text-[14px] leading-[17px] font-bold ${light ? "text-[#0a0a0a]" : "text-white"}`}>Hooper23</h2>
              <p className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>At practice · 34m</p>
            </div>
          </header>
          <div role="log" aria-label="Messages with Hooper23" aria-live="polite" className="relative flex w-full flex-col gap-[8px]">
            <p className={`w-[78%] rounded-[16px] px-[12px] pt-[11px] pb-[9px] text-[13px] leading-[16px] ${light ? "bg-[#f2f3f5] text-[#0a0a0a]" : "bg-[#17171b] text-white"}`}>You up for a run tonight?</p>
            {messages.map((message, index) => <p key={index} className={`ml-auto max-w-[85.22%] rounded-[16px] bg-blaze/10 px-[12px] pt-[11px] pb-[9px] text-[13px] leading-[16px] break-words ${light ? "text-[#0a0a0a]" : "text-white"}`}>{message}</p>)}
          </div>
          <form onSubmit={submit} className="relative flex h-[48px] w-full items-center gap-[10px]">
            <input aria-label="Message Hooper23" placeholder="Message Hooper23" value={draft} onChange={event => setDraft(event.target.value)} className={`h-[46px] min-w-0 flex-1 rounded-[14px] border px-[13px] text-[15px] leading-[18px] font-medium placeholder:text-[#757575] focus-visible:outline-2 focus-visible:outline-blaze ${light ? "border-[#e7e8ec] bg-[#f2f3f5] text-[#0a0a0a]" : "border-white/[0.09] bg-[#17171b] text-white"}`} />
            <PrimaryButton type="submit" className={`!w-[67.17px] shrink-0 ${light ? "!shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_6px_18px_rgba(255,106,0,0.35)]" : ""}`}>Send</PrimaryButton>
          </form>
        </SurfaceCard> : <p role="status" className="py-[14px] font-mono text-[11px] leading-[15px] text-muted">No conversations found</p>}
      </div>
    </div>
    <DashboardNavigation light={light} active="friends" className={light ? "!bottom-[-2px]" : "!left-[1.68px] !right-[-1.68px] !bottom-[0.17px]"} />
  </ScreenShell>;
}
