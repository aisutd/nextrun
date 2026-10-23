import type { Metadata } from "next";
import { FaceScanScreen } from "@/components/face-scan-screen";
export const metadata: Metadata = { title: "NextRun — Face scan" };
export default function FaceScanPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><FaceScanScreen /></main>;
}
