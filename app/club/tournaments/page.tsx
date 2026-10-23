import type { Metadata } from "next";
import { ClubTournaments } from "@/components/club-tournaments";
export const metadata: Metadata = { title: "NextRun — Club Tournaments" };
export default function ClubTournamentsPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><ClubTournaments /></main>;
}
