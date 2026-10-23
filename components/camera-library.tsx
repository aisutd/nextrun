import { ScreenShell } from "./screen-shell";
import { CameraHeader } from "./camera-header";
import { CameraTabs } from "./camera-tabs";
import { CameraProcessingQueue } from "./camera-processing-queue";
import { DashboardNavigation } from "./dashboard-navigation";

export function CameraLibrary({ light = false }: { light?: boolean }) {
  return <ScreenShell light={light} label="Scouting camera library" backgroundStyle={light ? { backgroundColor: "#fff", backgroundImage: "radial-gradient(ellipse 429px 286.96px at 100% 0%,rgba(255,106,0,0.1) 0%,rgba(255,106,0,0) 65%)" } : { backgroundColor: "#050506", backgroundOrigin: "border-box", backgroundImage: "radial-gradient(ellipse 429px 320.72px at 100% 0%,rgba(255,106,0,0.2) 0%,rgba(255,106,0,0) 65%),radial-gradient(ellipse 351px 286.96px at 0% 100%,rgba(255,106,0,0.09) 0%,rgba(255,106,0,0) 65%)" }}>
    <div className="absolute inset-0 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"><div className="relative min-h-full w-full pb-[90px]">
      <CameraHeader light={light} />
      <CameraTabs active="library" light={light} />
      <div className={`px-[16px] ${light ? "pt-[126px]" : "pt-[118px]"}`}><CameraProcessingQueue light={light} /></div>
    </div></div>
    <DashboardNavigation active="record" light={light} className={light ? "!bottom-[-2px]" : "!right-[-2px]"} />
  </ScreenShell>;
}
