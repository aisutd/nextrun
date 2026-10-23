import type { Metadata } from "next";
import { SettingsScreen } from "@/components/settings-screen";
export const metadata: Metadata = { title: "NextRun — Settings" };
export default function SettingsPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><SettingsScreen /></main>;
}
