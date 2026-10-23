import type { Metadata } from "next";
import { ClubLeaderboard } from "@/components/club-leaderboard";
export const metadata: Metadata = { title: "NextRun — Light Club Leaderboard" };
export default function LightClubLeaderboardPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><ClubLeaderboard light /></main>;
}
