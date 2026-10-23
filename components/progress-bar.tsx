type ProgressBarProps = { value: number; label: string; light?: boolean };

export function ProgressBar({ value, label, light = false }: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, value));
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage} className={`h-[7px] w-full overflow-hidden rounded-[8px] ${light ? "bg-[#f2f3f5]" : "bg-[#17171b]"}`}>
      <div style={{ width: `${percentage}%` }} className="h-full rounded-[8px] bg-linear-to-r from-[#993f00] to-blaze shadow-[0_0_18px_rgba(255,106,0,0.5)]" />
    </div>
  );
}
