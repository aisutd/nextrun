import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "NextRun — Welcome", description: "AI-powered basketball analytics, training, and community." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body className="font-sans antialiased">{children}</body></html>;
}
