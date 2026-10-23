import type { Metadata } from "next";
import { CustomPlayerCard } from "@/components/custom-player-card";
export const metadata: Metadata = { title: "NextRun — Custom Player Card" };
export default function CustomCardPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><CustomPlayerCard /></main>;
}
