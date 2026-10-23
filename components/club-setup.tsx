import { ScreenShell } from "./screen-shell";
import { ClubHeader } from "./club-header";
import { ClubTabs } from "./club-tabs";
import { ClubSetupForm } from "./club-setup-form";
import { DashboardNavigation } from "./dashboard-navigation";

export function ClubSetup({ light = false }: { light?: boolean }) {
  return <ScreenShell light={light} label="Club setup" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div data-setup-scroll className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <div className="relative min-h-full w-full pb-[100px]">
        <ClubHeader light={light} artwork={light ? "/figma/setup-light-header.svg" : "/figma/setup-header-art.svg"} />
        <ClubTabs active="setup" light={light} />
        <div className="px-[16px] pt-[221px]"><ClubSetupForm light={light} /></div>
      </div>
    </div>
    <DashboardNavigation active="club" light={light} className={light ? "!bottom-[-2px]" : "translate-x-[0.68px] translate-y-[-1.17px]"} />
  </ScreenShell>;
}
