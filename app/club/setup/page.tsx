import type { Metadata } from "next";
import { ClubSetup } from "@/components/club-setup";
export const metadata: Metadata = { title: "NextRun — Club Setup" };
export default function ClubSetupPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><ClubSetup /></main>;
}
