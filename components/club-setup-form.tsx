"use client";

import { useState, type FormEvent } from "react";
import { SurfaceCard } from "./surface-card";
import { VideoUploadCard } from "./video-upload-card";
import { PrimaryButton } from "./primary-button";

const inputClasses = "relative h-[46px] w-full shrink-0 rounded-[14px] border border-white/[0.09] bg-[#17171b] px-[13px] text-[15px] leading-[18px] font-medium text-white placeholder:text-[#757575]";

export function ClubSetupForm({ light = false }: { light?: boolean }) {
  const [saved, setSaved] = useState(false);
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    sessionStorage.setItem("nextrun.clubDraft", JSON.stringify(Object.fromEntries(data.entries())));
    setSaved(true);
  }
  return <>
    <SurfaceCard light={light} shadow={false} gradientAngle={160.24053930843053} aria-labelledby="register-club" className={`h-[267px] px-[14px] pt-[14px] pb-[24px] ${light ? "" : "shadow-[0_0_0_1px_rgba(255,106,0,0.07),0_0_26px_rgba(255,106,0,0.1)]"}`}>
      <form onSubmit={save} onChange={() => setSaved(false)} className="relative flex flex-col gap-[10px]">
        <h2 id="register-club" className={`h-[18px] font-display text-[15px] leading-[18px] font-extrabold tracking-[-0.15px] italic ${light ? "text-[#0a0a0a]" : "text-white"}`}>Register your club</h2>
        <input name="name" aria-label="Club name" placeholder="Club name" required className={`${inputClasses} ${light ? "!border-[#e7e8ec] !bg-[#f2f3f5] !text-[#0a0a0a]" : ""}`} />
        <input name="school" aria-label="Associated school" placeholder="Associated school" className={`${inputClasses} ${light ? "!border-[#e7e8ec] !bg-[#f2f3f5] !text-[#0a0a0a]" : ""}`} />
        <div className="flex h-[27px] items-center gap-[10px]"><p className={`min-w-0 flex-1 text-[13px] leading-[18.85px] ${light ? "text-[#5b6270]" : "text-muted"}`}>Club colors</p>{[{ name: "primaryColor", label: "Primary club color", value: "#ff6a00" }, { name: "secondaryColor", label: "Secondary club color", value: "#0a0a0a" }].map(color => <input key={color.name} type="color" name={color.name} aria-label={color.label} defaultValue={color.value} className="h-[27px] w-[50px] shrink-0 appearance-auto border border-black bg-[#efefef] px-[4px] py-px [&::-webkit-color-swatch-wrapper]:px-0 [&::-webkit-color-swatch-wrapper]:py-[4px] [&::-webkit-color-swatch]:border [&::-webkit-color-swatch]:border-[#777]" />)}</div>
        <PrimaryButton type="submit" className={`!h-[50px] !pt-[16px] !pb-[14px] ${light ? "!shadow-[inset_0_1px_0_rgba(255,255,255,0.35),0_6px_18px_rgba(255,106,0,0.35)]" : ""}`}>{saved ? "Draft saved" : "Create club"}</PrimaryButton>
      </form>
    </SurfaceCard>
    <div className="mt-[16px]">
      <VideoUploadCard light={light} artwork={light ? "/figma/camera-light-upload-art.svg" : undefined} />
    </div>
  </>;
}
