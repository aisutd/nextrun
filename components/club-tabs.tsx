import Link from "next/link";

const tabs = [
  { key: "leaderboard", label: "Leaderboard", width: 104.22, href: "/club/leaderboard", destination: "3345:3846" },
  { key: "activity", label: "Activity", width: 74.66, href: "/club/activity", destination: "3345:4127" },
  { key: "tournaments", label: "Tournaments", width: 106.73, href: "/club/tournaments", destination: "3345:4348" },
  { key: "setup", label: "Setup", width: 63.98, href: "/club/setup", destination: "3345:4533" },
] as const;

export function ClubTabs({ active, light = false }: { active: "leaderboard" | "activity" | "tournaments" | "setup"; light?: boolean }) {
  const activity = active === "activity";
  const positions = light ? activity ? [[6,6],[118.22,6],[201,6],[316,6]] : active === "tournaments" ? [[6,6],[118,6],[200.88,6],[316,6]] : [[6,6],[119,6],[202,6],[active === "leaderboard" ? 317 : 315.61,6]] : activity ? [[6, 6], [118.22, 6], [201, 7], [316, 6]] : active === "tournaments" ? [[6, 9], [118, 9], [200, 9], [315, 9]] : active === "setup" ? [[7, 6], [119, 6], [202, 6], [315.61, 6]] : [[7, 9], [119, 9], [202, 9], [317, 9]];
  return <nav aria-label="Club sections" className={`absolute h-[55px] overflow-x-auto rounded-[12px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${light ? "top-[166px] inset-x-[10px]" : "top-[165.83px] right-[3.32px] left-[16.68px]"}`}><div className="relative h-full w-[381px]">{tabs.map((tab, index) => {
    const selected = tab.key === active;
    const props = { style: { left: positions[index][0], top: positions[index][1], width: tab.width }, className: `absolute flex h-[37px] items-center justify-center rounded-full border text-[12px] leading-[15px] font-semibold ${selected ? `border-blaze bg-linear-to-b from-[#ff7f24] to-blaze text-white ${light ? "shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "shadow-[0_0_18px_rgba(255,106,0,0.5)]"}` : light ? "border-[#e7e8ec] bg-white text-[#5b6270]" : "border-white/[0.09] bg-[#0d0d0f] text-muted"}` };
    return <Link key={tab.key} {...props} href={light ? `${tab.href}/light` : tab.href} aria-current={selected ? "page" : undefined}>{tab.label}</Link>;
  })}</div></nav>;
}
