import type { Metadata } from "next";
import { CameraUpload } from "@/components/camera-upload";
export const metadata: Metadata = { title: "NextRun — Camera Upload" };
export default function CameraUploadPage() {
  return <main className="flex min-h-screen items-center justify-center bg-white px-[70px] py-[70px] max-[530px]:px-0 max-[530px]:py-0"><CameraUpload /></main>;
}
