import type { Metadata } from "next";
import { CameraLive } from "@/components/camera-live";
export const metadata: Metadata = { title: "NextRun — Scouting Camera" };
export default function CameraLivePage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><CameraLive /></main>;
}
