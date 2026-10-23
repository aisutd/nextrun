import type { Metadata } from "next";
import { RecordingTutorialScreen } from "@/components/recording-tutorial-screen";
export const metadata: Metadata = { title: "NextRun — How to record" };
export default function RecordingTutorialPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><RecordingTutorialScreen /></main>;
}
