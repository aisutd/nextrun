export function ProgressDots({ activeStep = 1, totalSteps = 5 }: { activeStep?: number; totalSteps?: number }) {
  return (
    <div aria-label={`Step ${activeStep} of ${totalSteps}`} className="flex h-[7px] w-full shrink-0 justify-center gap-[6px]">
      {Array.from({ length: totalSteps }, (_, index) => index + 1).map(step => <span key={step} aria-current={step === activeStep ? "step" : undefined} className={`h-[7px] shrink-0 rounded-[7px] ${step === activeStep ? "w-[22px] bg-blaze" : "w-[7px] bg-white/[0.09]"}`} />)}
    </div>
  );
}
