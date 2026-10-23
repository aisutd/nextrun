import Link from "next/link";
const tabs = [
  { label: "Live", key: "live", width: 101.14, href: "/camera/live" },
  { label: "Upload", key: "upload", width: 118.69, href: "/camera/upload" },
  { label: "Library", key: "library", width: 118.39, href: "/camera/library", destination: "3345:5185" },
] as const;

export function CameraTabs({ active, light = false }: { active: "live" | "upload" | "library"; light?: boolean }) {
  return <nav aria-label="Camera sections" className={`absolute inset-x-[10px] flex gap-[7.8px] overflow-x-auto rounded-[12px] px-[6px] pb-[12px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${active !== "live" ? "top-[55px] h-[63px] pt-[14px]" : "top-[63px] h-[55px] pt-[6px]"}`}>{tabs.map(tab => {
    const className = `flex h-[37px] shrink-0 items-center justify-center rounded-full border px-[14px] py-[10px] text-[12px] leading-[15px] font-semibold ${active === tab.key ? `border-blaze bg-linear-to-b from-[#ff7f24] to-blaze text-white ${light ? "shadow-[0_6px_18px_rgba(255,106,0,0.35)]" : "shadow-[0_0_18px_rgba(255,106,0,0.5)]"}` : light ? "border-[#e7e8ec] bg-white text-[#5b6270]" : "border-white/[0.09] bg-[#0d0d0f] text-muted"}`;
    return <Link key={tab.key} href={light ? `${tab.href}/light` : tab.href} aria-current={active === tab.key ? "page" : undefined} style={{ width: light ? {live: 102.47, upload: 120.02, library: 119.73}[tab.key] : tab.width }} className={className}>{tab.label}</Link>;
  })}</nav>;
}
