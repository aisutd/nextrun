import type { Metadata } from "next";
import { HomeDashboard } from "@/components/home-dashboard";
export const metadata: Metadata = { title: "NextRun — Home" };
export default function HomePage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><HomeDashboard /></main>;
}
