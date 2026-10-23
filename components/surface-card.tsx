import type { HTMLAttributes } from "react";

type SurfaceCardProps = HTMLAttributes<HTMLElement> & { gradientAngle?: number; shadowTop?: number; shadow?: boolean; light?: boolean };
/** Shared Figma dark surface; measured gradient angle and overlay offset vary by card. */
export function SurfaceCard({ children, className = "", gradientAngle = 159.99819542597163, shadowTop = -1, shadow = true, light = false, style, ...props }: SurfaceCardProps) {
  return (
    <section {...props} style={{ backgroundImage: light ? undefined : `linear-gradient(${gradientAngle}deg,rgba(255,255,255,0.05) 0%,rgba(255,255,255,0.008) 100%)`, ...style }} className={`relative w-full rounded-[18px] border ${light ? "border-[#e7e8ec] bg-white shadow-[0_10px_28px_rgba(18,20,30,0.07),0_1px_2px_rgba(18,20,30,0.06)]" : "border-blaze/[0.38] bg-[#0b0b0c]"} ${className}`}>
      {shadow && !light && <span aria-hidden="true" style={{ top: shadowTop }} className="pointer-events-none absolute inset-x-[-1px] bottom-[-1px] rounded-[18px] bg-white/[0.002] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]" />}
      {children}
    </section>
  );
}
