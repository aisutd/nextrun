import type { Metadata } from "next";
import { FriendsActive } from "@/components/friends-active";
export const metadata: Metadata = { title: "NextRun — Friends" };
export default function FriendsActivePage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><FriendsActive /></main>;
}
