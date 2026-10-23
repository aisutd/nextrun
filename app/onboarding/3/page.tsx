import type { Metadata } from "next";
import { WelcomeScreen } from "@/components/welcome-screen";
export const metadata: Metadata = { title: "NextRun — Better Players Build Stronger Communities" };
export default function OnboardingThreePage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><WelcomeScreen variant="onboarding-3" /></main>;
}
