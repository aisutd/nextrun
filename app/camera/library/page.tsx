import type { Metadata } from "next";
import { CameraLibrary } from "@/components/camera-library";
export const metadata: Metadata = { title: "NextRun — Camera Library" };
export default function CameraLibraryPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><CameraLibrary /></main>;
}
