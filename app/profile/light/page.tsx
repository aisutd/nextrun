import type { Metadata } from "next";
import { ProfileScreen } from "@/components/profile-screen";
export const metadata: Metadata = { title: "NextRun — Light Profile" };
export default function LightProfilePage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><ProfileScreen light /></main>;
}
