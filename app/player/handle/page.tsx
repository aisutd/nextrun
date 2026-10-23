import type { Metadata } from "next";
import { ScreenShell } from "@/components/screen-shell";
import { PlayerHandleForm } from "@/components/player-handle-form";
export const metadata: Metadata = { title: "NextRun — Create your player handle" };
export default function PlayerHandlePage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><ScreenShell label="Create your player handle" artwork="/figma/onboarding-basketball.svg"><PlayerHandleForm /></ScreenShell></main>;
}
