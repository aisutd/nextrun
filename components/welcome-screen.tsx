import { ScreenShell } from "./screen-shell";
import { ProgressDots } from "./progress-dots";
import { AuthButton } from "./auth-button";
import { Brand } from "./brand";

export function WelcomeScreen({ variant = "welcome" }: { variant?: "welcome" | "onboarding-2" | "onboarding-3" }) {
  const community = variant === "onboarding-3";
  const onboarding = variant !== "welcome";
  const activeSlide = community ? 3 : onboarding ? 2 : 1;
  return (
    <ScreenShell label="Welcome to NextRun" artwork={community ? "/figma/onboarding-community.svg" : onboarding ? "/figma/onboarding-basketball.svg" : "/figma/basketball-artwork.svg"}>
      <div className="relative flex w-full flex-col gap-[14px] px-[16px] pt-[18px] pb-[24px]">
        <div className={`flex min-h-[798px] w-full flex-col pt-[12px] ${community ? "gap-0" : onboarding ? "gap-[0.003px]" : "gap-[0.002px]"}`}>
          <header className={`flex h-[29px] w-full shrink-0 items-center justify-between ${community ? "mb-[-0.001px]" : ""}`}>
            <Brand />
            <span className="font-mono text-[10px] leading-[13px] font-semibold tracking-[2.2px] text-blaze uppercase">{community ? "Connect" : onboarding ? "Analyze" : "Play"}</span>
          </header>
          <div className={`flex w-full shrink-0 flex-col justify-end ${community ? "h-[757.001px] min-h-[605.86px] pt-[151.141px]" : onboarding ? "h-[756.997px] min-h-[624.7px] pt-[132.297px]" : "h-[756.998px] min-h-[588.31px] pt-[168.688px]"}`}>
            <div className={`flex w-full shrink-0 flex-col items-start pt-[200px] ${onboarding ? "gap-[4.9px]" : "gap-[5.2px]"}`}>
              <div className="flex h-[16px] w-full shrink-0 gap-[6px]" aria-label={`Slide ${activeSlide} of 3`}>
                {[1, 2, 3].map(slide => {
                  const active = slide === activeSlide;
                  return <button key={slide} type="button" aria-label={`Slide ${slide}`} aria-current={active ? "true" : undefined} className={`h-[16px] rounded-[6px] ${active ? "w-[42px] bg-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" : "w-[24px] bg-white/[0.09]"}`} />;
                })}
              </div>
              <h1 className={`w-full shrink-0 font-display text-[35px] leading-[36.4px] font-extrabold tracking-[-0.35px] text-white italic max-[389px]:text-[clamp(28px,8.97vw,35px)] ${onboarding ? "min-h-[110px]" : "pb-[0.585px]"}`}>
                {community ? <><span className="whitespace-nowrap">BETTER PLAYERS</span><br /><span className="whitespace-nowrap">BUILD STRONGER</span><br /><span className="text-blaze">COMMUNITIES</span></> : onboarding ? <>ANALYZE.<br />IMPROVE.<br /><span className="text-blaze">CONNECT.</span></> : <>YOUR JOURNEY<br />BUILDS <span className="text-blaze">LEGENDS</span></>}
              </h1>
              <p className={`w-full shrink-0 text-[13px] leading-[18.85px] text-muted ${community ? "pt-[5.1px] min-h-[24.1px]" : onboarding ? "pt-[4.52px] min-h-[42.52px]" : "pt-[4.22px]"}`}>
                {community ? "Train. Track. Compete. Together." : <>{onboarding ? "The next generation of basketball performance and" : "AI-powered basketball analytics, training, and"}<br className="max-[389px]:hidden" /> community.</>}
              </p>
              <p className={`w-full shrink-0 text-[13px] leading-[19px] text-muted ${community ? "pt-[1.11px] pb-[17.1px]" : onboarding ? "pt-[1.1px] pb-[17.1px]" : "pt-[0.8px] pb-[16.8px]"}`}>Sign in to keep your stats and card.</p>
              <AuthButton figmaDestination={community ? "3345:3308" : undefined} layout={onboarding ? "onboarding" : "welcome"} provider="email">Continue with email</AuthButton>
              <AuthButton figmaDestination={community ? "3345:3308" : undefined} layout={onboarding ? "onboarding" : "welcome"} provider="google">Continue with Google</AuthButton>
              <AuthButton figmaDestination={community ? "3345:3308" : undefined} layout={onboarding ? "onboarding" : "welcome"} provider="apple">Continue with Apple</AuthButton>
              <p className={`w-full shrink-0 text-center font-mono text-[11px] leading-[15px] text-muted ${onboarding ? "pt-[9.1px]" : "pt-[8.8px]"}`}>Track. Improve. Compete. Together.</p>
            </div>
          </div>
        </div>
        <ProgressDots />
      </div>
    </ScreenShell>
  );
}
