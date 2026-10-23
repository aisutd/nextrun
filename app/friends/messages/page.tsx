import type { Metadata } from "next";
import { FriendsMessages } from "@/components/friends-messages";
export const metadata: Metadata = { title: "NextRun — Friends Messages" };
export default function FriendsMessagesPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><FriendsMessages /></main>;
}
