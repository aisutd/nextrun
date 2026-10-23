import type { CSSProperties, ReactNode } from "react";

export function ScreenShell({ artwork, label, children, backgroundStyle, light = false }: { artwork?: string; label: string; children: ReactNode; backgroundStyle?: CSSProperties; light?: boolean }) {
  return (
    <section aria-label={label} style={backgroundStyle} className={`relative flex h-[844px] w-[390px] max-w-full shrink-0 flex-col overflow-hidden ${light ? "shadow-[0_30px_80px_rgba(0,0,0,0.16)]" : "border-2 border-blaze/[0.38] shadow-[0_0_70px_rgba(255,106,0,0.18)]"}`}>
      {artwork && <div aria-hidden="true" className="pointer-events-none absolute -left-[2px] top-0 h-[840px] w-[390px]">
        {/* Unmodified Figma artwork export; the interface remains semantic HTML. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={artwork} alt="" width={390} height={840} className="block max-w-none" />
      </div>}
      {!light && <><div aria-hidden="true" className="pointer-events-none absolute top-[252px] -left-[80px] size-[240px] rounded-[120px] bg-blaze/[0.28] opacity-[0.26] blur-[20px]" />
      <div aria-hidden="true" className="pointer-events-none absolute top-[488.81px] -right-[70px] size-[200px] rounded-[100px] bg-[#22d3ee]/[0.16] opacity-[0.26] blur-[20px]" /></>}
      {children}
    </section>
  );
}
