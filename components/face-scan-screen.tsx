import { ScreenShell } from "./screen-shell";
import { PrimaryLink } from "./primary-button";
import { ProgressBar } from "./progress-bar";
import { ProgressDots } from "./progress-dots";

/** Reproduces the completed scan state supplied by Figma. No camera or biometric processing is performed. */
export function FaceScanScreen() {
  return (
    <ScreenShell artwork="/figma/face-scan-background.svg" label="Face scan">
      <div className="relative h-[840px] w-full overflow-hidden">
        <h1 className="absolute inset-x-[16px] top-[48px] text-center font-display text-[28px] leading-[30.8px] font-extrabold tracking-[-0.28px] text-white italic">Face scan</h1>
        <p className="absolute inset-x-[15.5px] top-[78.8px] text-center text-[13px] leading-[18.85px] text-muted min-[390px]:whitespace-nowrap">Center your face so teammates can be tagged in footage.</p>
        <div aria-hidden="true" className="absolute top-[117.64px] left-1/2 h-[240px] w-[200px] -translate-x-1/2 overflow-hidden rounded-[22px] border-2 border-blaze bg-[radial-gradient(ellipse_175.72px_175.12px_at_100px_96px,#2a1505_0%,#000_100%)] shadow-[0_0_18px_rgba(255,106,0,0.5)]">
          {/* The exported guide already includes its Figma opacity. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/figma/face-guide.svg" alt="" width={196} height={236} className="block max-w-none" />
          <div className="absolute inset-x-0 top-0 h-[3px] bg-[#22d3ee] shadow-[0_0_16px_#22d3ee]" />
        </div>
        <div className="absolute inset-x-[16px] top-[377.64px]"><ProgressBar value={100} label="Face scan completed" /></div>
        <p className="absolute inset-x-[16px] top-[394.64px] text-center font-mono text-[11px] leading-[15px] text-muted">Face saved</p>
        <div className="absolute inset-x-[16px] top-[426.64px]"><PrimaryLink href="/player/clubs">Continue</PrimaryLink></div>
        <div className="absolute inset-x-[16px] top-[489.64px]"><ProgressDots activeStep={3} /></div>
      </div>
    </ScreenShell>
  );
}
