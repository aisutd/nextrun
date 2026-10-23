import type { Metadata } from "next";
import { FindClubsScreen } from "@/components/find-clubs-screen";
export const metadata: Metadata = { title: "NextRun — Find local clubs" };
export default function FindClubsPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><FindClubsScreen /></main>;
}
