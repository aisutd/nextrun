export function Brand({ light = false }: { light?: boolean }) {
  return (
    <div className="flex h-[29px] items-center" aria-label="NextRun">
      <span className={`font-display text-[24px] leading-[29px] font-extrabold italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Next<span className="text-blaze">Run</span></span>
      <span className="relative ml-[4px] block size-[22px]" aria-hidden="true">
        {/* Figma's export includes 5px of shadow on all sides. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={light ? "/figma/dashboard-light-runner.svg" : "/figma/runner.svg"} alt="" width={32} height={32} className="absolute -top-[5px] -left-[5px] max-w-none" />
      </span>
    </div>
  );
}
