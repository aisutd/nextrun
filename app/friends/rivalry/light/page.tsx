import type { Metadata } from "next";
import { FriendsRivalry } from "@/components/friends-rivalry";
export const metadata: Metadata = { title: "NextRun — Light Friends Rivalry" };
export default function LightFriendsRivalryPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><FriendsRivalry light /></main>;
}
