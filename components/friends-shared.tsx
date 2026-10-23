import Link from "next/link";

export function FriendsHeader({ light = false }: { light?: boolean }) {
 return (
        <header className={`absolute inset-x-[16px] top-[18px] h-[108px] overflow-hidden rounded-[22px] border ${light ? "border-[#e7e8ec] shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-white/[0.09] shadow-[0_0_26px_rgba(255,106,0,0.1)]"}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={light ? "/figma/friends-light-header-art.svg" : "/figma/friends-header-art.svg"} alt="" width={light ? 358 : 354} height={108} className={`absolute -top-px -left-px h-[108px] max-w-none ${light ? "w-[358px]" : "w-[354px]"}`} />
          <div aria-hidden="true" className={`absolute inset-0 bg-linear-to-b ${light ? "from-white/5 to-[#f4f3f0]/80" : "from-black/10 to-black/70"}`} />
          <div className="absolute top-[34px] left-[18px] flex flex-col gap-[2px]">
            <p className="font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">Squad</p>
            <h1 className={`font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>The Crew</h1>
            <p className={`font-mono text-[11px] leading-[15px] ${light ? "text-[#5b6270]" : "text-muted"}`}>4 online now</p>
          </div>
        </header>
 );
}

export function FriendsSearch({query, onQueryChange, light = false}: {query: string; onQueryChange: (query: string) => void; light?: boolean}) {
 return (
        <div className="absolute inset-x-[16px] top-[138px]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={light ? "/figma/friends-light-search.svg" : "/figma/friends-search.svg"} alt="" width={18} height={18} className="pointer-events-none absolute top-[14px] left-[14px] z-10" />
          <input type="search" aria-label="Search friends, clubs, handles" placeholder="Search friends, clubs, handles" value={query} onChange={event => onQueryChange(event.target.value)} className={`h-[46px] w-full rounded-[14px] border pr-[13px] pl-[42px] text-[15px] leading-[18px] font-medium placeholder:text-[#757575] focus-visible:outline-2 focus-visible:outline-blaze ${light ? "border-[#e7e8ec] bg-[#f2f3f5] text-[#0a0a0a]" : "border-white/[0.09] bg-[#17171b] text-white"}`} />
        </div>
 );
}

export function FriendsTabs({active, light = false}: {active: "Active" | "Messages" | "Rivalry"; light?: boolean}) {
 return (
        <nav aria-label="Friends sections" className="absolute inset-x-[10px] top-[189px] flex gap-[7.8px] overflow-x-auto rounded-[12px] px-[6px] pt-[6px] pb-[12px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {[{ label: "Active", width: 104.09, destination: "3345:5250" }, { label: "Messages", width: 126.81, destination: "3345:5436" }, { label: "Rivalry", width: 107.33, destination: "3345:5564" }].map(tab => { const className = `flex h-[37px] shrink-0 items-center justify-center rounded-full border text-[12px] leading-[15px] font-semibold ${tab.label === active ? `border-blaze bg-linear-to-b from-[#ff7f24] to-blaze text-white ${light ? "shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "shadow-[0_0_18px_rgba(255,106,0,0.5)]"}` : light ? "border-[#e7e8ec] bg-white text-[#5b6270]" : "border-white/[0.09] bg-[#0d0d0f] text-muted"}`; return <Link href={tab.label === "Active" ? (light ? "/friends/active/light" : "/friends/active") : tab.label === "Messages" ? (light ? "/friends/messages/light" : "/friends/messages") : light ? "/friends/rivalry/light" : "/friends/rivalry"} key={tab.label} aria-current={tab.label === active ? "page" : undefined} style={{ width: tab.width + (light ? 1.33 : 0) }} className={className}>{tab.label}</Link>; })}
        </nav>
 );
}
