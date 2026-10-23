import type { Metadata } from "next";
import { ClubActivity } from "@/components/club-activity";
export const metadata: Metadata = { title: "NextRun — Light Club Activity" };
export default function LightClubActivityPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><ClubActivity light /></main>;
}
