import Link from "next/link";
import { primaryButtonClasses } from "./primary-button";
import type { ReactNode } from "react";
type AuthButtonProps = { provider: "email" | "google" | "apple"; children: ReactNode; layout?: "welcome" | "onboarding"; figmaDestination?: string };
/** Visual sign-in control. Authentication can be wired once a provider is configured. */
export function AuthButton({ provider, children, layout = "welcome", figmaDestination }: AuthButtonProps) {
  const email = provider === "email";
  const google = provider === "google";
  const onboarding = layout === "onboarding";
  const secondaryLayout = onboarding
    ? google ? "h-[62.2px] px-[14px] py-[19.1px]" : "h-[50px] p-[14px]"
    : `${google ? "h-[56.8px]" : "h-[54.8px]"} px-[14px] pt-[18.8px] pb-[14px]`;
  const shadowPosition = onboarding
    ? google ? "inset-x-[-1px] inset-y-[4.1px]" : "inset-[-1px]"
    : "inset-x-[-1px] top-[3.8px] bottom-[-1px]";
  const className = `relative flex w-full shrink-0 items-center justify-center gap-[10px] rounded-[16px] border text-[15px] leading-[18px] font-semibold text-white ${email ? `h-[50px] p-[14px] ${primaryButtonClasses}` : `${secondaryLayout} border-white/[0.09] bg-[#0d0d0f]`}`;
  const content = <>
      {!email && <span aria-hidden="true" className={`pointer-events-none absolute ${shadowPosition} rounded-[16px] bg-white/[0.002] shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]`} />}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <span className={`relative flex shrink-0 items-center justify-center ${google ? "h-[22px] w-[14px]" : "size-[20px]"}`}><img src={`/figma/${provider}.svg`} alt="" width={google ? 13 : 20} height={google ? 14 : 20} className="block shrink-0 max-w-none" /></span>
      <span className="relative whitespace-nowrap">{children}</span>
    </>;
  const href = figmaDestination === "3345:3308" ? "/player/handle" : undefined;
  return href ? <Link href={href} data-provider={provider} data-figma-destination={figmaDestination} className={className}>{content}</Link> : <button type="button" data-provider={provider} className={className}>{content}</button>;
}
