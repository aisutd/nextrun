import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export const primaryButtonClasses = "border-blaze bg-linear-to-b from-[#ff7f24] to-blaze shadow-[inset_0_1px_0_0px_rgba(255,255,255,0.35),0_0_18px_rgba(255,106,0,0.5)]";
const primaryControlClasses = `relative flex h-[48px] w-full items-center justify-center rounded-[16px] border p-[14px] text-center text-[15px] leading-[18px] font-semibold text-white ${primaryButtonClasses}`;

export function PrimaryButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={`${primaryControlClasses} disabled:opacity-40 ${className}`} />;
}

export function PrimaryLink({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return <Link href={href} className={`${primaryControlClasses} ${className}`}>{children}</Link>;
}
