import Link from "next/link";

const items = [
  { label: "Home", icon: "home", destination: "3345:3574", width: "w-[59px]", href: "/home" },
  { label: "Club Hub", icon: "club", destination: "3345:3846", width: "w-[57px]", href: "/club/leaderboard" },
  { label: "Record", icon: "record", destination: "3345:4818", width: "w-[56px]", href: "/camera/live" },
  { label: "Friends", icon: "friends", destination: "3345:5250", width: "w-[52.44px]", href: "/friends/active" },
  { label: "Profile", icon: "profile", destination: "3345:5698", width: "w-[52.12px]", href: "/profile" },
] as const;

/** Original five-item navigation. Destinations are connected as their screens are implemented. */
export function DashboardNavigation({ active = "home", light = false, className: extraClassName = "" }: { active?: "home" | "club" | "record" | "friends" | "profile"; className?: string; light?: boolean }) {
  return (
    <nav aria-label="Main navigation" className={`absolute inset-x-0 bottom-0 z-20 h-[69px] px-[10px] pb-[10px] ${extraClassName}`}>
      <div className={`relative flex h-[59px] items-center gap-[16.3px] rounded-[28px] border border-blaze/[0.38] bg-[#0b0b0c] px-[6px] pt-[8px] pb-[10px] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)] max-[389px]:gap-[clamp(5px,3.09vw,12px)] ${light ? "!justify-center !gap-[17.1px] !border-[#e7e8ec] !bg-white !shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)] max-[389px]:!gap-[12px]" : ""}`}>
        {items.map(item => {
          const record = item.icon === "record";
          const className = `relative flex shrink-0 flex-col items-center ${record && (active === "record" || light) ? "w-[58px]" : light && item.icon === "home" ? "w-[52.75px]" : item.width} ${record ? "h-[30px]" : "h-[39px] gap-[3px] py-px"} ${item.icon === active ? "text-blaze" : light ? "text-[#5b6270]" : "text-muted"}`;
          const content = <>
            <span className={record ? `absolute top-[-28px] left-0 flex size-[58px] items-center justify-center rounded-[29px] ${light && active !== "record" ? "bg-[radial-gradient(circle_56.26px_at_20.3px_16.24px,#ff974d,#ff6a00)] shadow-[0_0_0_6px_white,0_0_0_7px_rgba(255,106,0,0.35),0_6px_18px_rgba(255,106,0,0.35)]" : active === "record" ? "bg-blaze shadow-[0_0_0_6px_#fe4234,0_0_0_8px_rgba(12,12,13,0.35)]" : "bg-[radial-gradient(circle_56.26px_at_20.3px_16.24px,#ff974d,#ff6a00)] shadow-[0_0_0_6px_#0b0b0c,0_0_0_7px_rgba(255,106,0,0.35),0_0_18px_rgba(255,106,0,0.5)]"}` : "block size-[22px]"}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={light ? `/figma/nav-light-${item.icon}${item.icon === "home" && active === "home" ? "-active" : item.icon === "club" && active === "club" ? "-active" : record && active === "record" ? "-active" : item.icon === "friends" && active === "friends" ? "-active" : item.icon === "profile" && active !== "profile" ? "-inactive" : ""}.svg` : `/figma/nav-${item.icon}${item.icon === "home" && active !== "home" ? "-inactive" : (item.icon === "club" && active === "club") || (record && active === "record") || (item.icon === "friends" && active === "friends") || (item.icon === "profile" && active === "profile") ? "-active" : ""}.svg`} alt="" width={22} height={22} className="block max-w-none" />
            </span>
            {!record && <span className={`text-[10px] leading-[12px] font-medium whitespace-nowrap ${(item.icon === "home" && active === "home" || light && item.icon === active) ? "[text-shadow:0_0_12px_rgba(255,106,0,0.6)]" : ""}`}>{item.label}</span>}
          </>;
          return <Link key={item.icon} href={light && item.icon === "home" ? "/home/light" : light && item.icon === "club" ? "/club/leaderboard/light" : light && record ? "/camera/live/light" : light && item.icon === "profile" ? "/profile/light" : light && item.icon === "friends" ? "/friends/active/light" : item.href} aria-label={item.label} aria-current={item.icon === active ? "page" : undefined} className={className}>{content}</Link>;
        })}
      </div>
    </nav>
  );
}
