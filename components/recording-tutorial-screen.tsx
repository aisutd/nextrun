import { ScreenShell } from "./screen-shell";
import { SurfaceCard } from "./surface-card";
import { ProgressDots } from "./progress-dots";
import { PrimaryLink } from "./primary-button";

export function RecordingTutorialScreen() {
  return (
    <ScreenShell artwork="/figma/recording-background.svg" label="How to record">
      <div className="relative flex w-full flex-col items-start gap-[14px] px-[16px] pt-[38px]">
        <h1 className="h-[31px] w-full shrink-0 font-display text-[28px] leading-[30.8px] font-extrabold tracking-[-0.28px] text-white italic">How to record</h1>
        <SurfaceCard aria-labelledby="recording-step-title" gradientAngle={159.66829492934312} shadowTop={3} className="flex shrink-0 flex-col items-center gap-[5.4px] px-[16px] pt-[30px] pb-[26px]">
          <div className="relative h-[116.656px] w-[200px] shrink-0 overflow-hidden" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/figma/recording-court.svg" alt="" width={200} height={117} className="block max-w-none" />
          </div>
          <h2 id="recording-step-title" className="relative w-full shrink-0 pt-[13.59px] text-center font-display text-[20px] leading-[24px] font-extrabold tracking-[-0.2px] text-white italic">Stand back</h2>
          <p className="relative min-h-[38px] w-full shrink-0 text-center text-[13px] leading-[18.85px] text-muted">Keep your phone steady at half-court height so the<br className="max-[389px]:hidden" /> full court is visible.</p>
          <p className="relative w-full shrink-0 pt-[6.6px] text-center font-mono text-[11px] leading-[15px] text-muted">Swipe or tap to continue</p>
        </SurfaceCard>
        <ProgressDots totalSteps={3} />
        <PrimaryLink href="/home">Next</PrimaryLink>
      </div>
    </ScreenShell>
  );
}
